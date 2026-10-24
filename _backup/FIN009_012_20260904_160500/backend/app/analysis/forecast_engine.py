from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..models.valuation_engine_models import (
    ForecastAssumptions,
    ForecastBundle,
    ForecastScenario,
    ForecastYear,
)


class ForecastEngineError(ValueError):
    pass


def _validate(a: ForecastAssumptions, years: int) -> None:
    if years <= 0:
        raise ForecastEngineError("forecast years must be positive")
    if len(a.revenue_growth) != years or len(a.ebit_margin) != years:
        raise ForecastEngineError("growth and margin assumptions must match forecast horizon")
    if not Decimal("0") <= a.tax_rate <= Decimal("0.60"):
        raise ForecastEngineError("tax rate out of supported range")
    for g in a.revenue_growth:
        if g <= Decimal("-0.90") or g > Decimal("2.00"):
            raise ForecastEngineError("revenue growth assumption out of supported range")
    for m in a.ebit_margin:
        if m < Decimal("-0.50") or m > Decimal("0.80"):
            raise ForecastEngineError("ebit margin assumption out of supported range")
    for name, x in (
        ("depreciation_to_revenue", a.depreciation_to_revenue),
        ("capex_to_revenue", a.capex_to_revenue),
        ("nwc_to_revenue", a.nwc_to_revenue),
    ):
        if x < Decimal("0") or x > Decimal("1"):
            raise ForecastEngineError(f"{name} out of supported range")


def build_fcff_forecast(
    name: str,
    *,
    base_year: int,
    base_revenue: Decimal,
    base_nwc: Decimal,
    assumptions: ForecastAssumptions,
) -> ForecastScenario:
    if base_revenue <= 0:
        raise ForecastEngineError("base revenue must be positive")
    _validate(assumptions, len(assumptions.revenue_growth))

    revenue = base_revenue
    prior_nwc = base_nwc
    rows: list[ForecastYear] = []
    for i, (growth, margin) in enumerate(zip(assumptions.revenue_growth, assumptions.ebit_margin), start=1):
        revenue = revenue * (Decimal("1") + growth)
        ebit = revenue * margin
        nopat = ebit * (Decimal("1") - assumptions.tax_rate)
        depreciation = revenue * assumptions.depreciation_to_revenue
        capex = revenue * assumptions.capex_to_revenue
        nwc = revenue * assumptions.nwc_to_revenue
        delta_nwc = nwc - prior_nwc
        fcff = nopat + depreciation - capex - delta_nwc
        rows.append(ForecastYear(base_year + i, revenue, ebit, nopat, depreciation, capex, nwc, delta_nwc, fcff))
        prior_nwc = nwc
    return ForecastScenario(name.upper(), base_year, base_revenue, tuple(rows), assumptions)


def build_three_scenario_forecast(
    symbol: str,
    as_of_date: date,
    *,
    base_year: int,
    base_revenue: Decimal,
    base_nwc: Decimal,
    bear: ForecastAssumptions,
    base: ForecastAssumptions,
    bull: ForecastAssumptions,
    confidence: str = "MEDIUM",
) -> ForecastBundle:
    horizons = {len(bear.revenue_growth), len(base.revenue_growth), len(bull.revenue_growth)}
    if len(horizons) != 1:
        raise ForecastEngineError("all scenarios must use the same forecast horizon")
    if confidence not in {"HIGH", "MEDIUM", "LOW"}:
        raise ForecastEngineError("invalid confidence")
    return ForecastBundle(
        symbol=symbol,
        as_of_date=as_of_date,
        bear=build_fcff_forecast("BEAR", base_year=base_year, base_revenue=base_revenue, base_nwc=base_nwc, assumptions=bear),
        base=build_fcff_forecast("BASE", base_year=base_year, base_revenue=base_revenue, base_nwc=base_nwc, assumptions=base),
        bull=build_fcff_forecast("BULL", base_year=base_year, base_revenue=base_revenue, base_nwc=base_nwc, assumptions=bull),
        confidence=confidence,
        warnings=(),
    )
