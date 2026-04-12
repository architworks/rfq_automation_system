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
            schedule_answers=[
                ExtractedField(
                    id="sched_claim_1",
                    label="Quoted total price",
                    field_group="schedule_answer",
                    schedule_id="pricing_schedule",
                    schedule_column_id="total_fee",
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
            technical_claims=[],
            commercial_claims=[],
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
            schedule_answers=[
                ExtractedField(
                    id="sched_claim_1",
                    label="Quoted total price",
                    field_group="schedule_answer",
                    schedule_id="pricing_schedule",
                    schedule_column_id="total_fee",
                    criterion_ids=["crit_commercial"],
                    line_item_id=artifact.rfq_snapshot.line_items[0].id,
                    state=ResponseState.ANSWERED,
                    raw_value="100 without currency",
                    numeric_value=100,
                    uom="Lot",
                    evidence=[],
                )
            ],
            technical_claims=[],
            commercial_claims=[],
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


def test_count_based_units_align_without_mathematical_conversion() -> None:
    artifact = _build_artifact()
    artifact.rfq_snapshot.line_items[0].uom = "Count"
    review = build_vendor_review(
        vendor_id="vendor_alpha",
        document=_build_document("alpha.pdf"),
        raw_extraction=RawExtraction(
            document_summary="Alpha summary",
            question_answers=[],
            schedule_answers=[
                ExtractedField(
                    id="sched_claim_1",
                    label="Quoted total price",
                    field_group="schedule_answer",
                    schedule_id="pricing_schedule",
                    schedule_column_id="total_fee",
                    criterion_ids=["crit_commercial"],
                    line_item_id=artifact.rfq_snapshot.line_items[0].id,
                    state=ResponseState.ANSWERED,
                    raw_value="USD 100 for 100 units",
                    numeric_value=100,
                    quantity_value=100,
                    currency="USD",
                    uom="units",
                    evidence=[],
                )
            ],
            technical_claims=[],
            commercial_claims=[],
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
    assert first_line.base_currency_total == 100
    assert first_line.uom == "count"
    assert first_line.target_uom == "count"


def test_schedule_answers_are_the_canonical_source_for_normalized_pricing() -> None:
    artifact = _build_artifact()
    review = build_vendor_review(
        vendor_id="vendor_alpha",
        document=_build_document("alpha.pdf"),
        raw_extraction=RawExtraction(
            document_summary="Alpha summary",
            question_answers=[],
            schedule_answers=[
                ExtractedField(
                    id="sched_li1_quote_status",
                    label="Quote status",
                    field_group="schedule_answer",
                    schedule_id="sched_commercial_quote",
                    schedule_column_id="quote_status",
                    line_item_id=artifact.rfq_snapshot.line_items[0].id,
                    state=ResponseState.ANSWERED,
                    raw_value="Quoted Price: EUR 315,000",
                    evidence=[
                        EvidenceAnchor(
                            id="ev_schedule_price",
                            snippet="Quoted Price EUR 315,000",
                            locator="page 2, pricing schedule",
                            source_label="alpha.pdf",
                        )
                    ],
                ),
                ExtractedField(
                    id="sched_li1_amount",
                    label="Quoted amount (USD)",
                    field_group="schedule_answer",
                    schedule_id="sched_commercial_quote",
                    schedule_column_id="amount_usd",
                    line_item_id=artifact.rfq_snapshot.line_items[0].id,
                    state=ResponseState.MISSING_EXTRACTABLE_EVIDENCE,
                    raw_value="EUR 315,000",
                    currency="EUR",
                    evidence=[
                        EvidenceAnchor(
                            id="ev_schedule_amount",
                            snippet="EUR 315,000",
                            locator="page 2, pricing schedule",
                            source_label="alpha.pdf",
                        )
                    ],
                ),
            ],
            technical_claims=[],
            commercial_claims=[],
            warnings=[],
        ),
        artifact=artifact,
        comparison_settings=ComparisonSettings(
            base_currency="EUR",
            fx_effective_date="2026-04-11",
            fx_rates=[],
        ),
    )

    first_line = review.normalized_pricing[0]
    assert first_line.comparability_status == "comparable"
    assert first_line.total_price == 315000
    assert first_line.base_currency_total == 315000
    assert first_line.currency == "EUR"
    assert "sched_li1_quote_status" in first_line.source_field_ids
    assert "Recovered numeric total price from extracted text" in " ".join(first_line.conversion_notes)


def test_commercial_claims_alone_do_not_drive_normalized_pricing() -> None:
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
                    id="claim_only_1",
                    label="Strategy price note",
                    field_group="commercial_claim",
                    line_item_id=artifact.rfq_snapshot.line_items[0].id,
                    state=ResponseState.ANSWERED,
                    raw_value="EUR 315,000",
                    numeric_value=315000,
                    currency="EUR",
                    evidence=[],
                )
            ],
            warnings=[],
        ),
        artifact=artifact,
        comparison_settings=ComparisonSettings(
            base_currency="EUR",
            fx_effective_date="2026-04-11",
            fx_rates=[],
        ),
    )

    first_line = review.normalized_pricing[0]
    assert first_line.comparability_status == "non_comparable"
    assert first_line.total_price is None
    assert first_line.base_currency_total is None
    assert first_line.blockers == ["No commercial schedule answer was extracted for this RFQ line item."]


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
