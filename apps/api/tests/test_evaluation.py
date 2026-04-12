from __future__ import annotations

from datetime import UTC, datetime

from rfq_api.models import (
    ComparisonSettings,
    Criterion,
    CriterionType,
    DeterministicScoringGuide,
    DeterministicScoringRule,
    DeterministicScoringType,
    DownloadMetadata,
    EvidenceCheck,
    ExtractedField,
    FXRate,
    GovernanceInfo,
    LLMSettings,
    LockedFrameworkArtifact,
    ResponseState,
    VendorDocument,
    VendorRecord,
    VendorStatus,
)
from rfq_api.seeds import build_seed_rfq
from rfq_api.services.evaluation import EvaluationContext, _evaluate_pass_fail, run_evaluation
from rfq_api.services.review import build_vendor_review

from .conftest import FakeLLMClient, build_valid_rubric_proposal


def test_evaluate_pass_fail_accepts_explicit_confirm_and_no_exclusions_language() -> None:
    guide = DeterministicScoringGuide(
        guide_type=DeterministicScoringType.PASS_FAIL,
        answer_format="Narrative confirmation",
        summary="Pass if the answer confirms the requirement clearly.",
        rules=[
            DeterministicScoringRule(id="rule_pass", condition="Requirement is confirmed clearly.", outcome="pass"),
            DeterministicScoringRule(id="rule_fail", condition="Requirement is missing or unclear.", outcome="fail"),
        ],
    )

    confirm_field = ExtractedField(
        id="field_confirm",
        label="Compliance confirmation",
        field_group="question_answer",
        state=ResponseState.ANSWERED,
        raw_value="We explicitly confirm that we can support child-directed advertising and claims review.",
    )
    quoted_field = ExtractedField(
        id="field_quote",
        label="Commercial quote completeness",
        field_group="question_answer",
        state=ResponseState.ANSWERED,
        raw_value="All applicable RFQ line items are quoted below. No RFQ line item is excluded.",
    )

    confirm_passed, _confirm_rule, _confirm_explanation = _evaluate_pass_fail(guide, confirm_field)
    quoted_passed, _quoted_rule, _quoted_explanation = _evaluate_pass_fail(guide, quoted_field)

    assert confirm_passed is True
    assert quoted_passed is True


def test_commercial_like_mac_is_excluded_from_technical_gate() -> None:
    proposal = build_valid_rubric_proposal()
    proposal.criteria.append(
        Criterion(
            id="crit_quote_mac",
            section_id="sec_compliance",
            title="Commercial quote completeness",
            description="Commercial pricing quote completeness and exclusions clarity.",
            criterion_type=CriterionType.MAC,
            evidence_checks=[
                EvidenceCheck(
                    id="ev_quote_mac",
                    label="Commercial quote check",
                    description="Commercial pricing data is present for downstream comparison.",
                )
            ],
            linked_schedule_fields=["pricing_schedule.total_fee"],
            deterministic_scoring=DeterministicScoringGuide(
                guide_type=DeterministicScoringType.PASS_FAIL,
                answer_format="Pricing schedule completeness",
                summary="Pass if commercial pricing data is present.",
                rules=[
                    DeterministicScoringRule(
                        id="rule_quote_pass",
                        condition="Commercial pricing data is present.",
                        outcome="pass",
                    ),
                    DeterministicScoringRule(
                        id="rule_quote_fail",
                        condition="Commercial pricing data is missing or incomplete.",
                        outcome="fail",
                    ),
                ],
            ),
        )
    )
    artifact = LockedFrameworkArtifact(
        locked_at=datetime.now(UTC),
        rfq_snapshot=build_seed_rfq(),
        rubric_snapshot=proposal,
        governance=GovernanceInfo(
            official_award_basis="QCBS 70/30",
            technical_threshold_strategy="Test threshold strategy",
            advisory_outputs=["LCS", "QBS", "RFQ-specific AI scenarios"],
            persistence_scope="Test scope",
        ),
        download_metadata=DownloadMetadata(file_name="artifact.json"),
    )
    vendor = VendorRecord(
        id="vendor_alpha",
        name="Alpha",
        status=VendorStatus.EXTRACTED,
        document=_build_document("alpha.pdf"),
    )
    llm = FakeLLMClient()
    raw_extraction = llm.extract_vendor_response(
        artifact=artifact,
        vendor=vendor,
        document=vendor.document,
        document_bytes=b"%PDF-1.4 alpha",
        llm_settings=LLMSettings(),
    )
    comparison_settings = ComparisonSettings(
        base_currency="USD",
        fx_effective_date="2026-04-11",
        fx_rates=[FXRate(currency="USD", rate_to_base=1.0)],
    )
    review = build_vendor_review(
        vendor_id=vendor.id,
        document=vendor.document,
        raw_extraction=raw_extraction,
        artifact=artifact,
        comparison_settings=comparison_settings,
    )
    context = EvaluationContext(
        artifact=artifact,
        comparison_settings=comparison_settings,
        vendors=[vendor],
        reviews_by_vendor={vendor.id: review},
        llm_settings=LLMSettings(),
    )

    report = run_evaluation(context, llm)

    assert report.technical_results[0].passed_gate is True
    assert all(
        "Commercial quote completeness" not in reason
        for reason in report.technical_results[0].disqualification_reasons
    )
    assert report.official_recommendation.winner_vendor_id == vendor.id


def _build_document(file_name: str) -> VendorDocument:
    return VendorDocument(
        file_name=file_name,
        mime_type="application/pdf",
        extension=".pdf",
        size_bytes=128,
        uploaded_at=datetime.now(UTC),
        warnings=[],
    )
