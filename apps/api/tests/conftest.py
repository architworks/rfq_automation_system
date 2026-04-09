from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from rfq_api.main import app, get_llm_client, get_session_store
from rfq_api.models import (
    Criterion,
    CriterionType,
    DeterministicScoringGuide,
    DeterministicScoringRule,
    DeterministicScoringType,
    EvidenceCheck,
    Question,
    ResponseSchedule,
    RubricProposal,
    RubricSection,
    ScheduleColumn,
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


@pytest.fixture
def client() -> TestClient:
    store = SessionStore(ttl_seconds=7200)
    app.dependency_overrides[get_session_store] = lambda: store
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
