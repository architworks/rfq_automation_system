from __future__ import annotations

from datetime import UTC, datetime

from rfq_api.models import (
    ComparisonSettings,
    DownloadMetadata,
    EvidenceAnchor,
    ExtractedField,
    FXRate,
    GovernanceInfo,
    LockedFrameworkArtifact,
    RawExtraction,
    ResponseState,
    VendorDocument,
)
from rfq_api.seeds import build_seed_rfq
from rfq_api.services.review import build_vendor_review

from .conftest import build_valid_rubric_proposal


def test_response_state_mapping_marks_missing_extractable_evidence_as_needs_buyer_input() -> None:
    artifact = _build_artifact()
    review = build_vendor_review(
        vendor_id="vendor_alpha",
        document=_build_document("alpha.pdf"),
        raw_extraction=RawExtraction(
            document_summary="Alpha summary",
            question_answers=[
                ExtractedField(
                    id="field_q1",
                    label="Capability confirmation",
                    field_group="question_answer",
                    question_id="q1",
                    criterion_ids=["crit_mac"],
                    state=ResponseState.MISSING_EXTRACTABLE_EVIDENCE,
                    raw_value=None,
                    evidence=[],
                )
            ],
            schedule_answers=[],
            technical_claims=[],
            commercial_claims=[],
            warnings=[],
        ),
        artifact=artifact,
        comparison_settings=None,
    )

    assert review.normalized_fields[0].comparability_status == "needs_buyer_input"


def test_known_uom_conversion_can_normalize_pricing_line() -> None:
    artifact = _build_artifact()
    artifact.rfq_snapshot.line_items[0].uom = "kg"
    review = build_vendor_review(
        vendor_id="vendor_alpha",
        document=_build_document("alpha.pdf"),
        raw_extraction=RawExtraction(
            document_summary="Alpha summary",
            question_answers=[],
            schedule_answers=[],
            technical_claims=[],
            commercial_claims=[
                ExtractedField(
                    id="claim_1",
                    label="Strategy price",
                    field_group="commercial_claim",
                    criterion_ids=["crit_commercial"],
                    line_item_id=artifact.rfq_snapshot.line_items[0].id,
                    state=ResponseState.ANSWERED,
                    raw_value="USD 100 per g basis",
                    numeric_value=100,
                    currency="USD",
                    uom="g",
                    evidence=[
                        EvidenceAnchor(
                            id="ev_1",
                            snippet="USD 100 quoted on a grams basis.",
                            locator="pricing table",
                            source_label="alpha.pdf",
                        )
                    ],
                )
            ],
            warnings=[],
        ),
        artifact=artifact,
        comparison_settings=ComparisonSettings(
            base_currency="USD",
            fx_effective_date="2026-04-11",
            fx_rates=[FXRate(currency="USD", rate_to_base=1.0)],
        ),
    )

    first_line = review.normalized_pricing[0]
    assert first_line.comparability_status == "comparable"
    assert first_line.base_currency_total == 0.1


def test_missing_currency_marks_pricing_line_non_comparable() -> None:
    artifact = _build_artifact()
    review = build_vendor_review(
        vendor_id="vendor_alpha",
        document=_build_document("alpha.pdf"),
        raw_extraction=RawExtraction(
            document_summary="Alpha summary",
            question_answers=[],
            schedule_answers=[],
            technical_claims=[],
            commercial_claims=[
                ExtractedField(
                    id="claim_1",
                    label="Strategy price",
                    field_group="commercial_claim",
                    criterion_ids=["crit_commercial"],
                    line_item_id=artifact.rfq_snapshot.line_items[0].id,
                    state=ResponseState.ANSWERED,
                    raw_value="100 without currency",
                    numeric_value=100,
                    uom="Lot",
                    evidence=[],
                )
            ],
            warnings=[],
        ),
        artifact=artifact,
        comparison_settings=ComparisonSettings(
            base_currency="USD",
            fx_effective_date="2026-04-11",
            fx_rates=[FXRate(currency="USD", rate_to_base=1.0)],
        ),
    )

    first_line = review.normalized_pricing[0]
    assert first_line.comparability_status == "non_comparable"
    assert "No currency could be extracted" in first_line.blockers[0]


def _build_artifact() -> LockedFrameworkArtifact:
    return LockedFrameworkArtifact(
        locked_at=datetime.now(UTC),
        rfq_snapshot=build_seed_rfq(),
        rubric_snapshot=build_valid_rubric_proposal(),
        governance=GovernanceInfo(
            official_award_basis="QCBS 70/30",
            technical_threshold_strategy="Test threshold strategy",
            advisory_outputs=["LCS", "QBS", "RFQ-specific AI scenarios"],
            persistence_scope="Test scope",
        ),
        download_metadata=DownloadMetadata(file_name="artifact.json"),
    )


def _build_document(file_name: str) -> VendorDocument:
    return VendorDocument(
        file_name=file_name,
        mime_type="application/pdf",
        extension=".pdf",
        size_bytes=128,
        uploaded_at=datetime.now(UTC),
        warnings=[],
    )
