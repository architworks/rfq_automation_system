from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
import re

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
from .normalization_catalog import (
    lookup_deterministic_uom_factor,
    normalize_uom_token,
    supported_currency_codes,
)


_COMMERCIAL_FIELD_HINTS = (
    "price",
    "amount",
    "fee",
    "quote",
    "quoted",
    "cost",
    "currency",
    "uom",
    "quantity",
    "exclusion",
    "assumption",
    "commercial",
)
_COMMERCIAL_NOTE_HINTS = (
    "note",
    "notes",
    "exclusion",
    "assumption",
    "comment",
    "remark",
)
_MONEY_WITH_CODE_PATTERN = re.compile(
    r"(?:(?P<currency>[A-Z]{3})\s*(?P<amount>[-+]?\d[\d,]*(?:\.\d+)?)|(?P<amount_alt>[-+]?\d[\d,]*(?:\.\d+)?)\s*(?P<currency_alt>[A-Z]{3}))"
)
_NUMBER_PATTERN = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")
_SUPPORTED_CURRENCY_CODES = frozenset(supported_currency_codes())


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
            status = ComparabilityStatus.NON_COMPARABLE
            blockers.append("Automatic currency normalization is unavailable for the locked RFQ base currency.")
        elif field.currency and comparison_settings is not None and field.numeric_value is not None:
            fx_rate = _lookup_fx_rate(comparison_settings, field.currency)
            if fx_rate is None:
                status = ComparabilityStatus.NON_COMPARABLE
                blockers.append(f"Missing FX rate for {field.currency} in the stored FX snapshot.")
            else:
                base_currency_value = field.numeric_value * fx_rate
                conversion_notes.append(
                    f"Converted {field.currency} to {comparison_settings.base_currency} using the stored FX snapshot dated {comparison_settings.fx_effective_date}."
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
                uom=normalize_uom_token(field.uom),
                target_uom=normalize_uom_token(field.uom),
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
    schedule_fields_by_line_item: dict[str, list[ExtractedField]] = defaultdict(list)
    for field in raw_extraction.schedule_answers:
        if field.line_item_id and _is_commercial_schedule_field(field):
            schedule_fields_by_line_item[field.line_item_id].append(field)

    pricing_lines: list[NormalizedPricingLine] = []

    for line_item in artifact.rfq_snapshot.line_items:
        matched_schedule_fields = schedule_fields_by_line_item.get(line_item.id, [])
        candidate = _resolve_pricing_candidate(schedule_fields=matched_schedule_fields)

        if candidate is None:
            pricing_lines.append(
                NormalizedPricingLine(
                    line_item_id=line_item.id,
                    line_item_name=line_item.product_name,
                    comparability_status=ComparabilityStatus.NON_COMPARABLE,
                    target_uom=line_item.uom,
                    blockers=["No commercial schedule answer was extracted for this RFQ line item."],
                )
            )
            continue

        uom = normalize_uom_token(candidate["uom"])
        target_uom = normalize_uom_token(line_item.uom)
        blockers: list[str] = []
        commercial_notes: list[str] = list(candidate["field_notes"])
        conversion_notes: list[str] = list(candidate["recovery_notes"])
        status = _base_comparability_for_state(candidate["state"])

        if candidate["state"] == ResponseState.CONFLICTING_EVIDENCE:
            status = ComparabilityStatus.NON_COMPARABLE
            blockers.append("Commercial response contains conflicting evidence.")
        elif candidate["state"] not in {
            ResponseState.ANSWERED,
            ResponseState.MISSING_EXTRACTABLE_EVIDENCE,
        }:
            blockers.append(f"Commercial response state is {candidate['state'].value}.")

        if candidate["numeric_value"] is None:
            status = ComparabilityStatus.NON_COMPARABLE
            blockers.append("No numeric total price could be extracted.")

        base_total = None
        if candidate["currency"] is None:
            status = ComparabilityStatus.NON_COMPARABLE
            blockers.append("No currency could be extracted for this RFQ line item.")
        elif comparison_settings is None:
            status = ComparabilityStatus.NON_COMPARABLE
            blockers.append("Automatic currency normalization is unavailable for the locked RFQ base currency.")
        elif candidate["numeric_value"] is not None:
            fx_rate = _lookup_fx_rate(comparison_settings, candidate["currency"])
            if fx_rate is None:
                status = ComparabilityStatus.NON_COMPARABLE
                blockers.append(f"Missing FX rate for {candidate['currency']} in the stored FX snapshot.")
            else:
                base_total = candidate["numeric_value"] * fx_rate
                conversion_notes.append(
                    f"Converted {candidate['currency']} to {comparison_settings.base_currency} using the stored FX snapshot dated {comparison_settings.fx_effective_date}."
                )

        if uom and target_uom and uom != target_uom:
            conversion_factor = lookup_deterministic_uom_factor(from_uom=uom, to_uom=target_uom)
            if conversion_factor is None:
                status = ComparabilityStatus.NON_COMPARABLE
                blockers.append(
                    f"Quoted UOM {uom} does not match RFQ UOM {target_uom}, and only deterministic weight/volume conversion is allowed in this prototype."
                )
            elif base_total is not None:
                base_total *= conversion_factor
                conversion_notes.append(
                    f"Applied deterministic {uom}-to-{target_uom} conversion to align the quoted quantity with the RFQ unit."
                )

        pricing_lines.append(
            NormalizedPricingLine(
                line_item_id=line_item.id,
                line_item_name=line_item.product_name,
                quantity=candidate["quantity_value"],
                uom=uom,
                target_uom=target_uom,
                currency=candidate["currency"],
                total_price=candidate["numeric_value"],
                base_currency_total=base_total,
                comparability_status=status,
                exclusions=commercial_notes,
                source_field_ids=candidate["source_field_ids"],
                evidence_refs=candidate["evidence_refs"],
                conversion_notes=conversion_notes,
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


def _resolve_pricing_candidate(
    *,
    schedule_fields: list[ExtractedField],
) -> dict[str, object] | None:
    source_fields = _dedupe_fields(schedule_fields)
    if not source_fields:
        return None

    ordered_fields = sorted(
        source_fields,
        key=lambda field: (
            _commercial_field_priority(field),
            0 if field.state == ResponseState.ANSWERED else 1,
            0 if field.numeric_value is not None else 1,
            0 if field.currency else 1,
            field.id,
        ),
    )

    numeric_value: float | None = None
    currency: str | None = None
    quantity_value: float | None = None
    uom: str | None = None
    field_notes: list[str] = []
    recovery_notes: list[str] = []

    for field in ordered_fields:
        parsed_numeric, parsed_currency, parsed_notes = _extract_price_components(field)
        if numeric_value is None and parsed_numeric is not None:
            numeric_value = parsed_numeric
            recovery_notes.extend(parsed_notes)
        if currency is None and parsed_currency is not None:
            currency = parsed_currency
            recovery_notes.extend(parsed_notes)
        if quantity_value is None and field.quantity_value is not None:
            quantity_value = field.quantity_value
        if uom is None and field.uom:
            uom = field.uom
        if field.notes:
            field_notes.append(field.notes)
        elif _is_note_like_field(field) and field.raw_value:
            field_notes.append(field.raw_value)

    evidence_refs = list(
        dict.fromkeys(
            anchor.id
            for field in ordered_fields
            for anchor in field.evidence
        )
    )
    primary_state = _select_pricing_state(ordered_fields, numeric_value=numeric_value, currency=currency)

    return {
        "numeric_value": numeric_value,
        "currency": currency,
        "quantity_value": quantity_value,
        "uom": uom,
        "field_notes": list(dict.fromkeys(note for note in field_notes if note)),
        "recovery_notes": list(dict.fromkeys(note for note in recovery_notes if note)),
        "source_field_ids": [field.id for field in ordered_fields],
        "evidence_refs": evidence_refs,
        "state": primary_state,
    }


def _dedupe_fields(fields: list[ExtractedField]) -> list[ExtractedField]:
    deduped: list[ExtractedField] = []
    seen_ids: set[str] = set()
    for field in fields:
        if field.id in seen_ids:
            continue
        seen_ids.add(field.id)
        deduped.append(field)
    return deduped


def _is_commercial_schedule_field(field: ExtractedField) -> bool:
    if field.currency or field.numeric_value is not None or field.quantity_value is not None or field.uom:
        return True
    text = _field_text(field)
    return any(hint in text for hint in _COMMERCIAL_FIELD_HINTS)


def _commercial_field_priority(field: ExtractedField) -> int:
    text = _field_text(field)
    if any(token in text for token in ("total", "amount", "price", "fee", "quote", "quoted")):
        return 0
    if field.currency or field.numeric_value is not None:
        return 1
    if any(token in text for token in ("quantity", "uom", "unit", "currency")):
        return 2
    return 3


def _field_text(field: ExtractedField) -> str:
    parts = [
        field.label,
        field.schedule_id or "",
        field.schedule_column_id or "",
        field.raw_value or "",
        field.notes or "",
    ]
    return " ".join(parts).lower()


def _is_note_like_field(field: ExtractedField) -> bool:
    text = _field_text(field)
    return any(hint in text for hint in _COMMERCIAL_NOTE_HINTS)


def _extract_price_components(field: ExtractedField) -> tuple[float | None, str | None, list[str]]:
    numeric_value = field.numeric_value
    currency = _canonical_currency(field.currency)
    notes: list[str] = []
    raw_value = field.raw_value or ""

    parsed_currency, parsed_numeric = _parse_money_from_text(raw_value)
    if numeric_value is None and parsed_numeric is not None:
        numeric_value = parsed_numeric
        notes.append(f"Recovered numeric total price from extracted text in {field.label}.")
    if currency is None and parsed_currency is not None:
        currency = parsed_currency
        notes.append(f"Recovered currency code from extracted text in {field.label}.")
    if numeric_value is None and raw_value and currency is not None and _commercial_field_priority(field) <= 1:
        fallback_numeric = _parse_number_from_text(raw_value)
        if fallback_numeric is not None:
            numeric_value = fallback_numeric
            notes.append(f"Recovered numeric total price from extracted text in {field.label}.")

    return numeric_value, currency, notes


def _parse_money_from_text(value: str) -> tuple[str | None, float | None]:
    for match in _MONEY_WITH_CODE_PATTERN.finditer(value):
        currency = _canonical_currency(match.group("currency") or match.group("currency_alt"))
        amount = match.group("amount") or match.group("amount_alt")
        if currency is None or amount is None:
            continue
        parsed_amount = _coerce_number(amount)
        if parsed_amount is not None:
            return currency, parsed_amount
    return None, None


def _parse_number_from_text(value: str) -> float | None:
    match = _NUMBER_PATTERN.search(value)
    if match is None:
        return None
    return _coerce_number(match.group(0))


def _coerce_number(value: str) -> float | None:
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def _canonical_currency(value: str | None) -> str | None:
    if not value:
        return None
    canonical = value.strip().upper()
    if canonical in _SUPPORTED_CURRENCY_CODES:
        return canonical
    if len(canonical) == 3 and canonical.isalpha():
        return canonical
    return None


def _select_pricing_state(
    fields: list[ExtractedField],
    *,
    numeric_value: float | None,
    currency: str | None,
) -> ResponseState:
    if any(field.state == ResponseState.CONFLICTING_EVIDENCE for field in fields):
        return ResponseState.CONFLICTING_EVIDENCE
    if numeric_value is not None and currency is not None:
        return ResponseState.ANSWERED
    if any(field.state == ResponseState.ANSWERED for field in fields):
        return ResponseState.ANSWERED
    if any(field.state == ResponseState.MISSING_EXTRACTABLE_EVIDENCE for field in fields):
        return ResponseState.MISSING_EXTRACTABLE_EVIDENCE
    if any(field.state == ResponseState.MISSING_VENDOR_RESPONSE for field in fields):
        return ResponseState.MISSING_VENDOR_RESPONSE
    if any(field.state == ResponseState.NOT_APPLICABLE for field in fields):
        return ResponseState.NOT_APPLICABLE
    return fields[0].state
