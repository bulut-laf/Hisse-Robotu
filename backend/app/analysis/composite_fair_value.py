from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..models.valuation_engine_models import CompositeFairValueResult, ValuationModelInput


class CompositeValuationError(ValueError):
    pass


def _compose(models: tuple[ValuationModelInput, ...]) -> tuple[Decimal | None, tuple[tuple[str, Decimal, Decimal], ...], Decimal | None, list[str]]:
    usable = [m for m in models if m.fair_value_per_share is not None and m.fair_value_per_share > 0 and m.weight > 0]
    warnings: list[str] = []
    if len(usable) < 2:
        warnings.append("INSUFFICIENT_INDEPENDENT_MODELS")
        return None, (), None, warnings
    total_w = sum((m.weight for m in usable), Decimal("0"))
    if total_w <= 0:
        raise CompositeValuationError("total model weight must be positive")
    normalized = [(m.name, m.fair_value_per_share, m.weight / total_w) for m in usable]
    value = sum((fv * w for _, fv, w in normalized), Decimal("0"))
    lo = min(fv for _, fv, _ in normalized)
    hi = max(fv for _, fv, _ in normalized)
    dispersion = (hi - lo) / value if value > 0 else None
    if dispersion is not None and dispersion > Decimal("0.35"):
        warnings.append("HIGH_MODEL_DISPERSION")
    return value, tuple(normalized), dispersion, warnings


def combine_fair_values(
    symbol: str,
    as_of_date: date,
    *,
    bear_models: tuple[ValuationModelInput, ...],
    base_models: tuple[ValuationModelInput, ...],
    bull_models: tuple[ValuationModelInput, ...],
) -> CompositeFairValueResult:
    bear, _, _, wb = _compose(bear_models)
    base, weighted, dispersion, wbase = _compose(base_models)
    bull, _, _, wbu = _compose(bull_models)
    warnings = wb + wbase + wbu

    if base is None:
        confidence = "LOW"
    else:
        usable = len(weighted)
        low_conf = sum(1 for m in base_models if m.fair_value_per_share is not None and m.confidence == "LOW")
        if usable >= 3 and (dispersion is None or dispersion <= Decimal("0.20")) and low_conf == 0:
            confidence = "HIGH"
        elif usable >= 2 and (dispersion is None or dispersion <= Decimal("0.35")):
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

    if bear is not None and base is not None and bear > base:
        warnings.append("SCENARIO_ORDER_INVALID_BEAR_ABOVE_BASE")
    if bull is not None and base is not None and bull < base:
        warnings.append("SCENARIO_ORDER_INVALID_BULL_BELOW_BASE")

    return CompositeFairValueResult(symbol, as_of_date, bear, base, bull, weighted, confidence, dispersion, tuple(dict.fromkeys(warnings)))
