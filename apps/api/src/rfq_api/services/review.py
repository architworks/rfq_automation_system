from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from ..models import (
    ComparabilityStatus,
    ComparisonSettings,
    ExtractedField,
    LockedFrameworkArtifact,
    NormalizedField,
    NormalizedPricingLine,
    RawExtraction,
    ResponseState,
    VendorDocument,
    VendorReview,
)


def build_vendor_review(
    *,
    vendor_id: str,
    document: VendorDocument,
    raw_extraction: RawExtraction,
    artifact: LockedFrameworkArtifact,
    comparison_settings: ComparisonSettings | None,
    created_at: datetime | None = None,
) -> VendorReview:
    normalized_fields = _normalize_fields(raw_extraction, comparison_settings)
    normalized_pricing = _normalize_pricing(raw_extraction, artifact, comparison_settings)
    blockers = _collect_review_blockers(raw_extraction, normalized_pricing)
    warnings = list(dict.fromkeys([*document.warnings, *raw_extraction.warnings]))

    visual_fidelity_warning = document.warnings[0] if document.warnings else None

    return VendorReview(
        vendor_id=vendor_id,
        document=document,
        visual_fidelity_warning=visual_fidelity_warning,
        raw_extraction=raw_extraction,
        normalized_fields=normalized_fields,
        normalized_pricing=normalized_pricing,
        warnings=warnings,
        blockers=blockers,
        created_at=created_at or datetime.now(UTC),
    )


def _normalize_fields(
    raw_extraction: RawExtraction,
    comparison_settings: ComparisonSettings | None,
) -> list[NormalizedField]:
    normalized_fields: list[NormalizedField] = []
    evidence_lookup = _build_evidence_lookup(raw_extraction)

    for field in [
        *raw_extraction.question_answers,
        *raw_extraction.schedule_answers,
        *raw_extraction.technical_claims,
        *raw_extraction.commercial_claims,
    ]:
        conversion_notes: list[str] = []
        blockers: list[str] = []
        status = _base_comparability_for_state(field.state)
        base_currency_value = None

        if field.currency and comparison_settings is None:
            status = ComparabilityStatus.NEEDS_BUYER_INPUT
            blockers.append("Comparison settings are required to normalize multi-currency values.")
        elif field.currency and comparison_settings is not None and field.numeric_value is not None:
            fx_rate = _lookup_fx_rate(comparison_settings, field.currency)
            if fx_rate is None:
                status = ComparabilityStatus.NEEDS_BUYER_INPUT
                blockers.append(f"Missing FX rate for {field.currency}.")
            else:
                base_currency_value = field.numeric_value * fx_rate
                conversion_notes.append(
                    f"Converted {field.currency} to {comparison_settings.base_currency} using buyer-provided rate {fx_rate:g}."
                )

        normalized_fields.append(
            NormalizedField(
                id=field.id,
                label=field.label,
                field_group=field.field_group,
                criterion_ids=list(field.criterion_ids),
                line_item_id=field.line_item_id,
                source_field_ids=[field.id],
                normalized_value=field.normalized_hint or field.raw_value,
                quantity_value=field.quantity_value,
                numeric_value=field.numeric_value,
                currency=field.currency,
                base_currency_value=base_currency_value,
                uom=_normalize_uom(field.uom),
                target_uom=_normalize_uom(field.uom),
                comparability_status=status,
                conversion_notes=conversion_notes,
                blockers=blockers,
                evidence_refs=[anchor.id for anchor in field.evidence if anchor.id in evidence_lookup],
            )
        )

    return normalized_fields


def _normalize_pricing(
    raw_extraction: RawExtraction,
    artifact: LockedFrameworkArtifact,
    comparison_settings: ComparisonSettings | None,
) -> list[NormalizedPricingLine]:
    claims_by_line_item: dict[str, list[ExtractedField]] = defaultdict(list)
    for claim in raw_extraction.commercial_claims:
        if claim.line_item_id:
            claims_by_line_item[claim.line_item_id].append(claim)

    pricing_lines: list[NormalizedPricingLine] = []

    for line_item in artifact.rfq_snapshot.line_items:
        matched_claims = claims_by_line_item.get(line_item.id, [])
        if not matched_claims:
            pricing_lines.append(
                NormalizedPricingLine(
                    line_item_id=line_item.id,
                    line_item_name=line_item.product_name,
                    comparability_status=ComparabilityStatus.NON_COMPARABLE,
                    target_uom=line_item.uom,
                    blockers=["No commercial claim was extracted for this RFQ line item."],
                )
            )
            continue

        primary = matched_claims[0]
        uom = _normalize_uom(primary.uom)
        target_uom = _normalize_uom(line_item.uom)
        blockers: list[str] = []
        notes: list[str] = []
        status = _base_comparability_for_state(primary.state)

        if primary.state != ResponseState.ANSWERED:
            blockers.append(f"Commercial response state is {primary.state.value}.")

        if primary.numeric_value is None:
            status = ComparabilityStatus.NON_COMPARABLE
            blockers.append("No numeric total price could be extracted.")

        base_total = None
        if primary.currency is None:
            status = ComparabilityStatus.NON_COMPARABLE
            blockers.append("No currency could be extracted for this RFQ line item.")
        elif comparison_settings is None:
            status = ComparabilityStatus.NEEDS_BUYER_INPUT
            blockers.append("Comparison settings are required before currency normalization.")
        elif primary.numeric_value is not None:
            fx_rate = _lookup_fx_rate(comparison_settings, primary.currency)
            if fx_rate is None:
                status = ComparabilityStatus.NEEDS_BUYER_INPUT
                blockers.append(f"Missing FX rate for {primary.currency}.")
            else:
                base_total = primary.numeric_value * fx_rate
                notes.append(
                    f"Converted {primary.currency} to {comparison_settings.base_currency} using buyer-provided rate {fx_rate:g}."
                )

        if uom and target_uom and uom != target_uom:
            conversion_factor = _lookup_known_uom_factor(from_uom=uom, to_uom=target_uom) or _lookup_uom_override(
                comparison_settings,
                from_uom=uom,
                to_uom=target_uom,
                line_item_id=line_item.id,
            )
            if conversion_factor is None:
                status = ComparabilityStatus.NON_COMPARABLE
                blockers.append(
                    f"Quoted UOM {uom} does not match RFQ UOM {target_uom}, and no deterministic conversion or buyer override factor is configured."
                )
            elif base_total is not None:
                base_total *= conversion_factor
                notes.append(
                    (
                        f"Applied deterministic conversion factor {conversion_factor:g} to align quoted UOM {uom} "
                        f"with requested UOM {target_uom}."
                        if _lookup_known_uom_factor(from_uom=uom, to_uom=target_uom) is not None
                        else f"Applied buyer override factor {conversion_factor:g} to align quoted UOM {uom} with requested UOM {target_uom}."
                    )
                )

        pricing_lines.append(
            NormalizedPricingLine(
                line_item_id=line_item.id,
                line_item_name=line_item.product_name,
                quantity=primary.quantity_value,
                uom=uom,
                target_uom=target_uom,
                currency=primary.currency,
                total_price=primary.numeric_value,
                base_currency_total=base_total,
                comparability_status=status,
                exclusions=[primary.notes] if primary.notes else [],
                source_field_ids=[claim.id for claim in matched_claims],
                evidence_refs=[anchor.id for anchor in primary.evidence],
                conversion_notes=notes,
                blockers=blockers,
            )
        )

    return pricing_lines


def _collect_review_blockers(
    raw_extraction: RawExtraction,
    pricing_lines: list[NormalizedPricingLine],
) -> list[str]:
    blockers: list[str] = []
    for field in [*raw_extraction.question_answers, *raw_extraction.schedule_answers]:
        if field.state in {
            ResponseState.MISSING_VENDOR_RESPONSE,
            ResponseState.MISSING_EXTRACTABLE_EVIDENCE,
            ResponseState.CONFLICTING_EVIDENCE,
        }:
            blockers.append(f"{field.label}: {field.state.value.replace('_', ' ')}.")
    for line in pricing_lines:
        blockers.extend(f"{line.line_item_name}: {blocker}" for blocker in line.blockers)
    return list(dict.fromkeys(blockers))


def _base_comparability_for_state(state: ResponseState) -> ComparabilityStatus:
    if state == ResponseState.ANSWERED:
        return ComparabilityStatus.COMPARABLE
    if state == ResponseState.NOT_APPLICABLE:
        return ComparabilityStatus.INFORMATIONAL
    if state == ResponseState.MISSING_VENDOR_RESPONSE:
        return ComparabilityStatus.NON_COMPARABLE
    if state == ResponseState.CONFLICTING_EVIDENCE:
        return ComparabilityStatus.NON_COMPARABLE
    return ComparabilityStatus.NEEDS_BUYER_INPUT


def _build_evidence_lookup(raw_extraction: RawExtraction) -> dict[str, str]:
    evidence_lookup: dict[str, str] = {}
    for field in [
        *raw_extraction.question_answers,
        *raw_extraction.schedule_answers,
        *raw_extraction.technical_claims,
        *raw_extraction.commercial_claims,
    ]:
        for anchor in field.evidence:
            evidence_lookup[anchor.id] = anchor.snippet
    return evidence_lookup


def _lookup_fx_rate(comparison_settings: ComparisonSettings, currency: str) -> float | None:
    if currency.upper() == comparison_settings.base_currency.upper():
        return 1.0
    for rate in comparison_settings.fx_rates:
        if rate.currency.upper() == currency.upper():
            return rate.rate_to_base
    return None


def _lookup_uom_override(
    comparison_settings: ComparisonSettings | None,
    *,
    from_uom: str,
    to_uom: str,
    line_item_id: str,
) -> float | None:
    if comparison_settings is None:
        return 1.0 if from_uom == to_uom else None
    if from_uom == to_uom:
        return 1.0
    for override in comparison_settings.uom_overrides:
        if (
            override.from_uom.lower() == from_uom.lower()
            and override.to_uom.lower() == to_uom.lower()
            and (override.line_item_id is None or override.line_item_id == line_item_id)
        ):
            return override.factor
    return None


def _lookup_known_uom_factor(*, from_uom: str, to_uom: str) -> float | None:
    canonical_factors = {
        "g": 0.001,
        "kg": 1.0,
        "mg": 0.000001,
        "ml": 0.001,
        "l": 1.0,
        "litre": 1.0,
        "liter": 1.0,
        "unit": 1.0,
        "lot": 1.0,
    }
    if from_uom not in canonical_factors or to_uom not in canonical_factors:
        return None
    family_pairs = {
        ("g", "kg"),
        ("kg", "g"),
        ("mg", "g"),
        ("g", "mg"),
        ("ml", "l"),
        ("l", "ml"),
        ("ml", "litre"),
        ("litre", "ml"),
        ("ml", "liter"),
        ("liter", "ml"),
    }
    if (from_uom, to_uom) not in family_pairs:
        return None
    return canonical_factors[from_uom] / canonical_factors[to_uom]


def _normalize_uom(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip().lower()
    synonyms = {
        "lot": "lot",
        "lots": "lot",
        "ls": "lot",
        "lump sum": "lot",
        "each": "unit",
        "ea": "unit",
        "unit": "unit",
        "units": "unit",
        "gram": "g",
        "grams": "g",
        "kilogram": "kg",
        "kilograms": "kg",
        "milligram": "mg",
        "milligrams": "mg",
        "millilitre": "ml",
        "millilitres": "ml",
        "milliliter": "ml",
        "milliliters": "ml",
        "litres": "litre",
        "liters": "liter",
    }
    return synonyms.get(normalized, normalized)
