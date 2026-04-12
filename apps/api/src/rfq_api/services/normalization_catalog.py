from __future__ import annotations

from ..models import ComparisonSettings, FXRate


ECB_FX_EFFECTIVE_DATE = "2026-04-10"
ECB_FX_BASE_CURRENCY = "EUR"
ECB_FX_RATES_PER_EUR: dict[str, float] = {
    "AUD": 1.6561,
    "BRL": 5.9191,
    "CAD": 1.6187,
    "CHF": 0.9241,
    "CNY": 7.9967,
    "CZK": 24.365,
    "DKK": 7.4727,
    "GBP": 0.87105,
    "HKD": 9.1729,
    "HUF": 377.20,
    "IDR": 20020.25,
    "ILS": 3.5709,
    "INR": 108.7795,
    "ISK": 143.29,
    "JPY": 186.43,
    "KRW": 1737.06,
    "MXN": 20.3184,
    "MYR": 4.6434,
    "NOK": 11.1165,
    "NZD": 2.0034,
    "PHP": 70.088,
    "PLN": 4.2435,
    "RON": 5.0915,
    "SEK": 10.8360,
    "SGD": 1.4919,
    "THB": 37.592,
    "TRY": 52.3147,
    "USD": 1.1711,
    "ZAR": 19.2389,
}

DISPLAY_UOM_OPTIONS: list[dict[str, str]] = [
    {"value": "Lot", "label": "Lot", "family": "Services"},
    {"value": "Count", "label": "Count", "family": "Counts"},
    {"value": "mg", "label": "mg", "family": "Weight"},
    {"value": "g", "label": "g", "family": "Weight"},
    {"value": "kg", "label": "kg", "family": "Weight"},
    {"value": "mL", "label": "mL", "family": "Volume"},
    {"value": "L", "label": "L", "family": "Volume"},
]

ALLOWED_EXTRACTION_UOM_TOKENS = [option["value"] for option in DISPLAY_UOM_OPTIONS]

_UOM_SYNONYMS: dict[str, str] = {
    "lot": "lot",
    "lots": "lot",
    "ls": "lot",
    "lump sum": "lot",
    "count": "count",
    "counts": "count",
    "unit": "count",
    "units": "count",
    "piece": "count",
    "pieces": "count",
    "each": "count",
    "ea": "count",
    "mg": "mg",
    "milligram": "mg",
    "milligrams": "mg",
    "g": "g",
    "gram": "g",
    "grams": "g",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "ml": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "l": "l",
    "litre": "l",
    "litres": "l",
    "liter": "l",
    "liters": "l",
}

_WEIGHT_FACTORS_IN_KG = {
    "mg": 0.000001,
    "g": 0.001,
    "kg": 1.0,
}

_VOLUME_FACTORS_IN_LITRE = {
    "ml": 0.001,
    "l": 1.0,
}


def supported_currency_codes() -> list[str]:
    return [ECB_FX_BASE_CURRENCY, *sorted(ECB_FX_RATES_PER_EUR)]


def build_auto_comparison_settings(base_currency: str) -> ComparisonSettings | None:
    canonical_base = base_currency.strip().upper()
    if canonical_base not in supported_currency_codes():
        return None

    return ComparisonSettings(
        base_currency=canonical_base,
        fx_effective_date=ECB_FX_EFFECTIVE_DATE,
        fx_rates=[
            FXRate(
                currency=currency,
                rate_to_base=lookup_fx_rate_to_base(base_currency=canonical_base, currency=currency),
            )
            for currency in supported_currency_codes()
            if currency != canonical_base
        ],
        uom_overrides=[],
    )


def lookup_fx_rate_to_base(*, base_currency: str, currency: str) -> float:
    canonical_base = base_currency.strip().upper()
    canonical_currency = currency.strip().upper()
    if canonical_base == canonical_currency:
        return 1.0

    source_rate = _eur_reference_rate(canonical_currency)
    target_rate = _eur_reference_rate(canonical_base)
    if source_rate is None or target_rate is None:
        raise KeyError(f"Unsupported FX conversion from {canonical_currency} to {canonical_base}.")
    return target_rate / source_rate


def normalize_uom_token(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split()).strip().lower()
    return _UOM_SYNONYMS.get(normalized, normalized or None)


def lookup_deterministic_uom_factor(*, from_uom: str, to_uom: str) -> float | None:
    if from_uom == to_uom:
        return 1.0

    if from_uom in _WEIGHT_FACTORS_IN_KG and to_uom in _WEIGHT_FACTORS_IN_KG:
        return _WEIGHT_FACTORS_IN_KG[from_uom] / _WEIGHT_FACTORS_IN_KG[to_uom]

    if from_uom in _VOLUME_FACTORS_IN_LITRE and to_uom in _VOLUME_FACTORS_IN_LITRE:
        return _VOLUME_FACTORS_IN_LITRE[from_uom] / _VOLUME_FACTORS_IN_LITRE[to_uom]

    return None


def is_supported_currency(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().upper() in supported_currency_codes()


def _eur_reference_rate(currency: str) -> float | None:
    if currency == ECB_FX_BASE_CURRENCY:
        return 1.0
    return ECB_FX_RATES_PER_EUR.get(currency)
