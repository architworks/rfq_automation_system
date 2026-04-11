from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from rfq_api.main import app, get_llm_client, get_session_store
from rfq_api.models import (
    CommercialEvaluationResult,
    Criterion,
    CriterionType,
    DeterministicScoringGuide,
    DeterministicScoringRule,
    DeterministicScoringType,
    EvidenceCheck,
    EvidenceAnchor,
    ExtractedField,
    RawExtraction,
    Question,
    ResponseState,
    ResponseSchedule,
    RubricProposal,
    RubricSection,
    ScheduleColumn,
    ScenarioKind,
    ScenarioRankingItem,
    ScenarioResult,
    TechnicalCriterionResult,
    TechnicalCriterionStatus,
    TechnicalEvaluationResult,
)
from rfq_api.services.llm import LLMClient
from rfq_api.session_store import SessionStore


def build_valid_rubric_proposal() -> RubricProposal:
    return RubricProposal(
        sections=[
            RubricSection(
                id="sec_compliance",
                title="Compliance",
                description="Non-negotiable compliance checks.",
            ),
            RubricSection(
                id="sec_technical",
                title="Technical Quality",
                description="Scored technical evaluation.",
            ),
            RubricSection(
                id="sec_commercial",
                title="Commercial",
                description="Commercial schedules and terms.",
            ),
        ],
        criteria=[
            Criterion(
                id="crit_mac",
                section_id="sec_compliance",
                title="Kids advertising capability",
                description="Vendor must confirm capability to support child-directed advertising review.",
                criterion_type=CriterionType.MAC,
                evidence_checks=[
                    EvidenceCheck(
                        id="ev_mac",
                        label="Capability confirmation",
                        description="Look for explicit compliance confirmation.",
                    )
                ],
                linked_question_ids=["q1"],
            ),
            Criterion(
                id="crit_cutoff",
                section_id="sec_technical",
                title="Launch program governance",
                description="Evaluate governance depth and stakeholder management.",
                criterion_type=CriterionType.TECHNICAL_CUTOFF_BACKED,
                weight=40,
                min_cutoff=24,
                max_score=40,
                evidence_checks=[
                    EvidenceCheck(
                        id="ev_cutoff",
                        label="Governance approach",
                        description="Program governance plan and escalation model.",
                    )
                ],
                linked_question_ids=["q2"],
                linked_schedule_fields=["timeline_schedule.delivery_model"],
            ),
            Criterion(
                id="crit_score",
                section_id="sec_technical",
                title="Integrated launch quality",
                description="Assess integrated strategy and workstream cohesion.",
                criterion_type=CriterionType.TECHNICAL_SCORED_ONLY,
                weight=60,
                max_score=60,
                evidence_checks=[
                    EvidenceCheck(
                        id="ev_score",
                        label="Integrated launch approach",
                        description="Overall launch strategy and channel integration quality.",
                    )
                ],
                linked_question_ids=["q3"],
                linked_schedule_fields=["pricing_schedule.total_fee"],
            ),
            Criterion(
                id="crit_commercial",
                section_id="sec_commercial",
                title="Commercial quote completeness",
                description="Commercial data captured for downstream phases.",
                criterion_type=CriterionType.COMMERCIAL,
                evidence_checks=[
                    EvidenceCheck(
                        id="ev_commercial",
                        label="Commercial schedule",
                        description="Commercial assumptions and quote format.",
                    )
                ],
                linked_schedule_fields=["pricing_schedule.total_fee"],
                deterministic_scoring=DeterministicScoringGuide(
                    guide_type=DeterministicScoringType.PASS_FAIL,
                    answer_format="Schedule completeness",
                    summary="Pass if the commercial schedule is complete enough for downstream comparison.",
                    rules=[
                        DeterministicScoringRule(
                            id="rule_complete",
                            condition="All required commercial fields are populated.",
                            outcome="pass",
                        ),
                        DeterministicScoringRule(
                            id="rule_incomplete",
                            condition="Any required commercial field is missing.",
                            outcome="fail",
                        ),
                    ],
                ),
            ),
        ],
        aggregate_technical_threshold=65,
        questions=[
            Question(
                id="q1",
                text="Confirm child-directed advertising and claims review capability.",
                purpose="Validate compliance readiness.",
                linked_criteria=["crit_mac"],
            ),
            Question(
                id="q2",
                text="Describe program governance, escalation, and stakeholder model.",
                purpose="Evaluate governance strength.",
                linked_criteria=["crit_cutoff"],
            ),
            Question(
                id="q3",
                text="Describe your integrated launch strategy across all requested workstreams.",
                purpose="Evaluate end-to-end technical quality.",
                linked_criteria=["crit_score"],
            ),
        ],
        response_schedules=[
            ResponseSchedule(
                id="pricing_schedule",
                name="Pricing Schedule",
                purpose="Capture comparable commercial fields.",
                columns=[
                    ScheduleColumn(
                        id="total_fee",
                        label="Total Fee",
                        description="Quoted total program fee.",
                        required=True,
                    )
                ],
                linked_criteria=["crit_score", "crit_commercial"],
            ),
            ResponseSchedule(
                id="timeline_schedule",
                name="Timeline Schedule",
                purpose="Capture delivery and dependency commitments.",
                columns=[
                    ScheduleColumn(
                        id="delivery_model",
                        label="Delivery Model",
                        description="How the vendor will deliver the launch milestones.",
                        required=True,
                    )
                ],
                linked_criteria=["crit_cutoff"],
            ),
        ],
        generation_rationale=[
            "The rubric emphasizes compliance, governance, and integrated launch quality.",
            "A single critical cutoff is used for launch governance to avoid brittle over-gating.",
        ],
    )


class FakeLLMClient(LLMClient):
    def generate_rubric(self, _rfq_draft):
        return build_valid_rubric_proposal()

    def extract_vendor_response(self, *, artifact, vendor, document, document_bytes):
        del document_bytes

        profile = _vendor_profile(vendor.name)
        evidence = lambda suffix, snippet, locator: [
            EvidenceAnchor(
                id=f"{vendor.id}_{suffix}",
                snippet=snippet,
                locator=locator,
                source_label=document.file_name,
            )
        ]

        question_answers = [
            ExtractedField(
                id=f"{vendor.id}_q1",
                label="Kids advertising capability",
                field_group="question_answer",
                question_id="q1",
                criterion_ids=["crit_mac"],
                state=ResponseState.ANSWERED if profile["mac_pass"] else ResponseState.MISSING_EXTRACTABLE_EVIDENCE,
                raw_value="Yes, capability confirmed." if profile["mac_pass"] else None,
                evidence=evidence("mac", "Capability confirmation provided.", "page 1"),
            ),
            ExtractedField(
                id=f"{vendor.id}_q2",
                label="Launch governance",
                field_group="question_answer",
                question_id="q2",
                criterion_ids=["crit_cutoff"],
                state=ResponseState.ANSWERED,
                raw_value=f"Governance strength score {profile['governance_score']}.",
                numeric_value=float(profile["governance_score"]),
                evidence=evidence("governance", "Governance model, escalation path, and ownership provided.", "page 2"),
            ),
            ExtractedField(
                id=f"{vendor.id}_q3",
                label="Integrated launch quality",
                field_group="question_answer",
                question_id="q3",
                criterion_ids=["crit_score"],
                state=ResponseState.ANSWERED,
                raw_value=f"Integrated launch quality score {profile['quality_score']}.",
                numeric_value=float(profile["quality_score"]),
                evidence=evidence("quality", "Integrated channel and execution approach described.", "page 3"),
            ),
        ]

        schedule_answers = [
            ExtractedField(
                id=f"{vendor.id}_timeline_delivery_model",
                label="Delivery Model",
                field_group="schedule_answer",
                schedule_id="timeline_schedule",
                schedule_column_id="delivery_model",
                criterion_ids=["crit_cutoff"],
                state=ResponseState.ANSWERED,
                raw_value="Central program lead with regional workstream owners.",
                evidence=evidence("timeline", "Delivery model table captured.", "page 4"),
            ),
            ExtractedField(
                id=f"{vendor.id}_pricing_total_fee",
                label="Total Fee",
                field_group="schedule_answer",
                schedule_id="pricing_schedule",
                schedule_column_id="total_fee",
                criterion_ids=["crit_score", "crit_commercial"],
                state=ResponseState.ANSWERED,
                raw_value=f"{profile['currency']} {profile['line_item_total']}",
                numeric_value=float(profile["line_item_total"]),
                currency=profile["currency"],
                uom="Lot",
                evidence=evidence("price_schedule", "Pricing schedule total fee row captured.", "page 5"),
            ),
        ]

        technical_claims = [
            ExtractedField(
                id=f"{vendor.id}_claim_governance",
                label="Governance claim",
                field_group="technical_claim",
                criterion_ids=["crit_cutoff"],
                state=ResponseState.ANSWERED,
                raw_value=f"Governance capability assessed at {profile['governance_score']}.",
                numeric_value=float(profile["governance_score"]),
                evidence=evidence("claim_governance", "Named governance leads and escalation model found.", "page 2"),
            ),
            ExtractedField(
                id=f"{vendor.id}_claim_quality",
                label="Integrated launch claim",
                field_group="technical_claim",
                criterion_ids=["crit_score"],
                state=ResponseState.ANSWERED,
                raw_value=f"Integrated quality assessed at {profile['quality_score']}.",
                numeric_value=float(profile["quality_score"]),
                evidence=evidence("claim_quality", "Integrated launch execution approach found.", "page 3"),
            ),
        ]

        commercial_claims = []
        included_line_item_ids = artifact.rfq_snapshot.line_items
        if profile["missing_line_item"]:
            included_line_item_ids = artifact.rfq_snapshot.line_items[:-1]
        for line_item in included_line_item_ids:
            commercial_claims.append(
                ExtractedField(
                    id=f"{vendor.id}_{line_item.id}",
                    label=f"{line_item.product_name} price",
                    field_group="commercial_claim",
                    criterion_ids=["crit_commercial"],
                    line_item_id=line_item.id,
                    state=ResponseState.ANSWERED,
                    raw_value=f"{profile['currency']} {profile['line_item_total']}",
                    numeric_value=float(profile["line_item_total"]),
                    currency=profile["currency"],
                    uom=profile["uom"],
                    notes=profile["commercial_note"],
                    evidence=evidence(line_item.id, f"Quoted price for {line_item.product_name}.", "pricing table"),
                )
            )

        return RawExtraction(
            document_summary=f"Extracted proposal summary for {vendor.name}.",
            question_answers=question_answers,
            schedule_answers=schedule_answers,
            technical_claims=technical_claims,
            commercial_claims=commercial_claims,
            warnings=list(profile["warnings"]),
        )

    def score_narrative_technical(self, *, artifact, vendor, review, criteria):
        del artifact, review
        profile = _vendor_profile(vendor.name)
        scores_by_criterion = {
            "crit_cutoff": float(profile["governance_score"]),
            "crit_score": float(profile["quality_score"]),
        }
        evidence_ids = {
            "crit_cutoff": [f"{vendor.id}_governance", f"{vendor.id}_claim_governance"],
            "crit_score": [f"{vendor.id}_quality", f"{vendor.id}_claim_quality"],
        }
        return [
            TechnicalCriterionResult(
                criterion_id=criterion.id,
                title=criterion.title,
                criterion_type=criterion.criterion_type,
                status=TechnicalCriterionStatus.SCORED,
                score=min(scores_by_criterion.get(criterion.id, 0.0), criterion.max_score or 0.0),
                max_score=criterion.max_score,
                passed=None,
                confidence=0.86,
                explanation=f"Narrative score derived from the extracted {criterion.title.lower()} evidence.",
                evidence_refs=evidence_ids.get(criterion.id, []),
                math_trace=[f"Fake scorer returned {scores_by_criterion.get(criterion.id, 0.0):g}."],
                risks=[],
            )
            for criterion in criteria
        ]

    def generate_ai_scenarios(self, *, artifact, technical_results, commercial_results):
        del artifact
        commercial_by_vendor = {
            result.vendor_id: result
            for result in commercial_results
        }
        eligible = [
            result
            for result in technical_results
            if result.passed_gate
            and commercial_by_vendor.get(result.vendor_id) is not None
            and commercial_by_vendor[result.vendor_id].award_ready
        ]
        if not eligible:
            return []

        ranked_by_quality = sorted(eligible, key=lambda item: item.aggregate_score, reverse=True)
        ranked_by_cost = sorted(
            eligible,
            key=lambda item: commercial_by_vendor[item.vendor_id].comparable_total or float("inf"),
        )
        ranked_by_balance = sorted(
            eligible,
            key=lambda item: (
                0.7 * item.aggregate_score
                + 0.3 * (commercial_by_vendor[item.vendor_id].commercial_score or 0.0)
            ),
            reverse=True,
        )
        excluded_vendor_ids = [
            result.vendor_id
            for result in technical_results
            if result.vendor_id not in {item.vendor_id for item in eligible}
        ]
        scenario_sets = [
            ("Speed Weighted View", ranked_by_cost, "Favor vendors that minimize normalized cost while staying technically qualified."),
            ("Quality Resilience View", ranked_by_quality, "Favor vendors with the strongest technical evidence and governance depth."),
            ("Balanced Delivery View", ranked_by_balance, "Favor vendors that balance quality leadership with competitive normalized pricing."),
        ]
        scenarios: list[ScenarioResult] = []
        for name, ranking_source, basis in scenario_sets:
            scenarios.append(
                ScenarioResult(
                    scenario_name=name,
                    scenario_kind=ScenarioKind.ADVISORY_AI,
                    is_official=False,
                    winner_vendor_id=ranking_source[0].vendor_id,
                    excluded_vendor_ids=excluded_vendor_ids,
                    weighting_or_rule_basis=basis,
                    explanation=f"{name} selected {ranking_source[0].vendor_name} from the eligible vendor pool.",
                    evidence_refs=[],
                    ranking=[
                        ScenarioRankingItem(
                            vendor_id=result.vendor_id,
                            vendor_name=result.vendor_name,
                            score=result.aggregate_score,
                            notes=[],
                        )
                        for result in ranking_source
                    ],
                )
            )
        return scenarios


def _vendor_profile(name: str) -> dict[str, object]:
    normalized = name.strip().lower()
    profiles = {
        "alpha": {
            "mac_pass": True,
            "governance_score": 36,
            "quality_score": 54,
            "line_item_total": 100.0,
            "currency": "USD",
            "uom": "Lot",
            "commercial_note": None,
            "warnings": [],
            "missing_line_item": False,
        },
        "beta": {
            "mac_pass": True,
            "governance_score": 30,
            "quality_score": 48,
            "line_item_total": 110.0,
            "currency": "USD",
            "uom": "Lot",
            "commercial_note": None,
            "warnings": [],
            "missing_line_item": False,
        },
        "gamma": {
            "mac_pass": True,
            "governance_score": 20,
            "quality_score": 52,
            "line_item_total": 90.0,
            "currency": "USD",
            "uom": "Lot",
            "commercial_note": None,
            "warnings": [],
            "missing_line_item": False,
        },
        "delta": {
            "mac_pass": True,
            "governance_score": 35,
            "quality_score": 56,
            "line_item_total": 95.0,
            "currency": "EUR",
            "uom": "Lot",
            "commercial_note": "Quoted in EUR.",
            "warnings": [],
            "missing_line_item": False,
        },
        "incomplete": {
            "mac_pass": True,
            "governance_score": 34,
            "quality_score": 50,
            "line_item_total": 102.0,
            "currency": "USD",
            "uom": "Lot",
            "commercial_note": "One line item omitted.",
            "warnings": [],
            "missing_line_item": True,
        },
    }
    return profiles.get(
        normalized,
        {
            "mac_pass": True,
            "governance_score": 32,
            "quality_score": 50,
            "line_item_total": 105.0,
            "currency": "USD",
            "uom": "Lot",
            "commercial_note": None,
            "warnings": [],
            "missing_line_item": False,
        },
    )


@pytest.fixture
def client() -> TestClient:
    store = SessionStore(ttl_seconds=7200)
    app.dependency_overrides[get_session_store] = lambda: store
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
