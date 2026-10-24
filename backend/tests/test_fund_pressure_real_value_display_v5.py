from decimal import Decimal
from types import SimpleNamespace
from backend.app.ui.fund_analysis_center import fund_pressure_rows

def _profile():
    return SimpleNamespace(
        fund_concentration_risk=SimpleNamespace(score=None),
        exit_difficulty_risk=SimpleNamespace(score=None),
        active_selling_pressure=SimpleNamespace(score=None),
        data_quality_state=SimpleNamespace(value="VALID"),
        automatic_trade_authority="NONE",
    )

def test_sahol_real_small_values_are_visible():
    raw = SimpleNamespace(
        ownership=SimpleNamespace(fund_free_float_ratio=Decimal("0.000004384656942191513924606292160")),
        liquidity=SimpleNamespace(
            liquidation_days_normal=Decimal("0.001341558471675710216000897555"),
            liquidation_days_aggressive=Decimal("0.0006707792358378551080004487776"),
            liquidation_days_stress=Decimal("0.002745346023469996910898855030"),
        ),
    )
    row = fund_pressure_rows({"SAHOL": _profile()}, {"SAHOL": raw})[0]
    assert row["Fon/FDO %"] == 0.000438
    assert row["Likidasyon Normal (gün)"] == 0.001342
    assert row["Likidasyon Agresif (gün)"] == 0.000671
    assert row["Likidasyon Stres (gün)"] == 0.002745

def test_ttkom_real_small_values_are_visible():
    raw = SimpleNamespace(
        ownership=SimpleNamespace(fund_free_float_ratio=Decimal("0.00001812504631503603881252545466")),
        liquidity=SimpleNamespace(
            liquidation_days_normal=Decimal("0.002720592543040505761521948423"),
            liquidation_days_aggressive=Decimal("0.001360296271520252880760974212"),
            liquidation_days_stress=Decimal("0.005742595497453953051373621222"),
        ),
    )
    row = fund_pressure_rows({"TTKOM": _profile()}, {"TTKOM": raw})[0]
    assert row["Fon/FDO %"] == 0.001813
    assert row["Likidasyon Normal (gün)"] == 0.002721
    assert row["Likidasyon Agresif (gün)"] == 0.00136
    assert row["Likidasyon Stres (gün)"] == 0.005743
