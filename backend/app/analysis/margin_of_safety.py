from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..models.valuation_engine_models import MarginOfSafetyResult


class MarginOfSafetyError(ValueError):
    pass


def required_mos_for_confidence(confidence: str, *, cyclicality: str = "NORMAL") -> Decimal:
    base = {"HIGH": Decimal("0.15"), "MEDIUM": Decimal("0.20"), "LOW": Decimal("0.30")}
    if confidence not in base:
        raise MarginOfSafetyError("invalid confidence")
    mos = base[confidence]
    if cyclicality == "HIGH":
        mos += Decimal("0.05")
    elif cyclicality != "NORMAL":
        raise MarginOfSafetyError("invalid cyclicality")
    return min(mos, Decimal("0.40"))


def assess_margin_of_safety(
    symbol: str,
    as_of_date: date,
    *,
    current_price: Decimal,
    base_fair_value: Decimal,
    required_margin_of_safety: Decimal,
) -> MarginOfSafetyResult:
    if current_price <= 0 or base_fair_value <= 0:
        raise MarginOfSafetyError("price and fair value must be positive")
    if required_margin_of_safety < 0 or required_margin_of_safety >= Decimal("0.80"):
        raise MarginOfSafetyError("required margin of safety out of range")

    attractive_entry = base_fair_value * (Decimal("1") - required_margin_of_safety)
    upside = (base_fair_value / current_price) - Decimal("1")
    current_mos = Decimal("1") - (current_price / base_fair_value)

    if current_price <= attractive_entry * Decimal("0.90"):
        status = "VERY_ATTRACTIVE"
    elif current_price <= attractive_entry:
        status = "ATTRACTIVE"
    elif current_price <= base_fair_value * Decimal("1.05"):
        status = "FAIR"
    elif current_price <= base_fair_value * Decimal("1.20"):
        status = "EXPENSIVE"
    else:
        status = "VERY_EXPENSIVE"

    return MarginOfSafetyResult(symbol, as_of_date, current_price, base_fair_value, required_margin_of_safety, attractive_entry, upside, current_mos, status)
