from datetime import date
from decimal import Decimal

import pytest

from backend.app.analysis.composite_fair_value import combine_fair_values
from backend.app.analysis.dcf_valuation import DCFValuationError, value_fcfe, value_fcff
from backend.app.analysis.forecast_engine import ForecastEngineError, build_three_scenario_forecast
from backend.app.analysis.margin_of_safety import assess_margin_of_safety, required_mos_for_confidence
from backend.app.models.valuation_engine_models import ForecastAssumptions, ValuationModelInput


def D(x: str) -> Decimal:
    return Decimal(x)


def A(growth, margin):
    return ForecastAssumptions(
        revenue_growth=tuple(D(x) for x in growth),
        ebit_margin=tuple(D(x) for x in margin),
        tax_rate=D("0.25"),
        depreciation_to_revenue=D("0.035"),
        capex_to_revenue=D("0.045"),
        nwc_to_revenue=D("0.08"),
    )


def bundle():
    return build_three_scenario_forecast(
        "TUPRS", date(2026,8,4), base_year=2026, base_revenue=D("1200000000000"), base_nwc=D("90000000000"),
        bear=A(["-0.05","0.00","0.02","0.02","0.02"], ["0.06","0.065","0.07","0.07","0.07"]),
        base=A(["0.05","0.06","0.06","0.05","0.05"], ["0.085","0.09","0.095","0.095","0.095"]),
        bull=A(["0.10","0.10","0.08","0.07","0.06"], ["0.10","0.105","0.11","0.11","0.11"]),
        confidence="MEDIUM",
    )


def test_fin009_builds_three_explicit_scenarios():
    b = bundle()
    assert len(b.base.years) == 5
    assert b.bear.years[-1].revenue < b.base.years[-1].revenue < b.bull.years[-1].revenue


def test_fin009_fcff_is_derived_from_nopat_reinvestment_and_working_capital():
    row = bundle().base.years[0]
    expected = row.nopat + row.depreciation - row.capex - row.delta_nwc
    assert row.fcff == expected


def test_fin009_mismatched_horizons_fail_closed():
    with pytest.raises(ForecastEngineError):
        build_three_scenario_forecast(
            "X", date(2026,1,1), base_year=2026, base_revenue=D("100"), base_nwc=D("10"),
            bear=A(["0.01"],["0.1"]), base=A(["0.01","0.01"],["0.1","0.1"]), bull=A(["0.01"],["0.1"]),
        )


def test_fin010_fcff_dcf_bridges_enterprise_to_equity_with_net_debt():
    r = value_fcff(bundle().base, wacc=D("0.15"), terminal_growth=D("0.04"), net_debt=D("-100000000000"), diluted_shares=D("1926795773"))
    assert r.enterprise_value is not None and r.equity_value is not None
    assert r.equity_value > r.enterprise_value  # net cash adds to equity value
    assert r.fair_value_per_share is not None and r.fair_value_per_share > 0


def test_fin010_rejects_terminal_growth_at_or_above_discount_rate():
    with pytest.raises(DCFValuationError):
        value_fcff(bundle().base, wacc=D("0.10"), terminal_growth=D("0.10"), net_debt=D("0"), diluted_shares=D("100"))


def test_fin010_fcfe_values_equity_directly():
    r = value_fcfe((D("10"),D("11"),D("12"),D("13"),D("14")), scenario="BASE", cost_of_equity=D("0.14"), terminal_growth=D("0.03"), diluted_shares=D("10"))
    assert r.enterprise_value is None
    assert r.equity_value is not None
    assert r.fair_value_per_share == r.equity_value / D("10")


def M(name, value, weight, confidence="MEDIUM"):
    return ValuationModelInput(name, D(value) if value is not None else None, D(weight), confidence)


def test_fin011_requires_at_least_two_independent_models():
    r = combine_fair_values("TUPRS", date(2026,8,4), bear_models=(M("DCF","100","1"),), base_models=(M("DCF","120","1"),), bull_models=(M("DCF","140","1"),))
    assert r.base_value is None
    assert "INSUFFICIENT_INDEPENDENT_MODELS" in r.warnings


def test_fin011_composite_normalizes_weights_and_preserves_scenario_band():
    r = combine_fair_values(
        "TUPRS", date(2026,8,4),
        bear_models=(M("DCF","100","0.6"),M("PE","90","0.4")),
        base_models=(M("DCF","130","0.6"),M("PE","120","0.4")),
        bull_models=(M("DCF","160","0.6"),M("PE","150","0.4")),
    )
    assert r.bear_value < r.base_value < r.bull_value
    assert sum((w for _,_,w in r.weighted_models), D("0")) == D("1")


def test_fin011_high_dispersion_reduces_confidence():
    r = combine_fair_values(
        "TUPRS", date(2026,8,4),
        bear_models=(M("DCF","80","0.5"),M("PE","120","0.5")),
        base_models=(M("DCF","100","0.5"),M("PE","200","0.5")),
        bull_models=(M("DCF","150","0.5"),M("PE","260","0.5")),
    )
    assert r.confidence == "LOW"
    assert "HIGH_MODEL_DISPERSION" in r.warnings


def test_fin012_required_mos_rises_when_confidence_falls_or_cyclicality_high():
    assert required_mos_for_confidence("HIGH") == D("0.15")
    assert required_mos_for_confidence("LOW") == D("0.30")
    assert required_mos_for_confidence("MEDIUM", cyclicality="HIGH") == D("0.25")


def test_fin012_margin_of_safety_separates_fair_value_from_attractive_entry():
    r = assess_margin_of_safety("TUPRS", date(2026,8,4), current_price=D("150"), base_fair_value=D("200"), required_margin_of_safety=D("0.20"))
    assert r.attractive_entry_price == D("160")
    assert r.upside_downside_to_base == D("200") / D("150") - D("1")
    assert r.status == "ATTRACTIVE"


def test_fin012_expensive_when_price_above_fair_value():
    r = assess_margin_of_safety("TUPRS", date(2026,8,4), current_price=D("230"), base_fair_value=D("200"), required_margin_of_safety=D("0.20"))
    assert r.status == "EXPENSIVE"
