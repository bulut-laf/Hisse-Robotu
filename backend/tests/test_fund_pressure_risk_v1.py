from datetime import date
from decimal import Decimal

from backend.app.funds.contracts import DataQualityState
from backend.app.funds.pressure_risk import (
    PressureScoreStatus,
    StockFundPressureInput,
    build_pressure_profiles,
    calculate_concentration,
    calculate_exit_liquidity,
)

DAY = date(2026, 9, 1)


def test_concentration_and_fund_free_float_ratio():
    metric = calculate_concentration(
        {"A": Decimal("60"), "B": Decimal("30"), "C": Decimal("10")},
        free_float_shares=Decimal("400"),
    )
    assert metric.fund_owned_shares == Decimal("100")
    assert metric.fund_free_float_ratio == Decimal("0.25")
    assert metric.largest_fund_share == Decimal("0.6")
    assert metric.top3_fund_share == Decimal("1.0")
    assert metric.hhi == Decimal("0.46")


def test_exit_liquidity_has_normal_aggressive_and_stress_scenarios():
    metric = calculate_exit_liquidity(
        Decimal("1000000"),
        Decimal("500000"),
        stressed_liquidity_capacity=Decimal("25000"),
    )
    assert metric.liquidation_days_normal == Decimal("20")
    assert metric.liquidation_days_aggressive == Decimal("10")
    assert metric.liquidation_days_stress == Decimal("40")


def item(symbol: str, *, fund_ratio: str, top3: str, hhi: str, normal: str, stress: str,
         ownership_change: str, distribution: str, down_volume: str, return20: str,
         quality=DataQualityState.VALID):
    ownership = calculate_concentration(
        {"A": Decimal("1")},
        free_float_shares=Decimal("1"),
    )
    ownership = type(ownership)(
        fund_owned_shares=Decimal("1"),
        free_float_shares=Decimal("1"),
        fund_free_float_ratio=Decimal(fund_ratio),
        largest_fund_share=Decimal("1"),
        top3_fund_share=Decimal(top3),
        top5_fund_share=Decimal(top3),
        hhi=Decimal(hhi),
    )
    liquidity = calculate_exit_liquidity(Decimal("1"), Decimal("1"))
    liquidity = type(liquidity)(
        total_fund_position_value=Decimal("1"),
        adv20_value=Decimal("1"),
        median_daily_value_20=Decimal("1"),
        stressed_liquidity_capacity=Decimal("1"),
        liquidation_days_normal=Decimal(normal),
        liquidation_days_aggressive=Decimal(normal) / Decimal("2"),
        liquidation_days_stress=Decimal(stress),
    )
    return StockFundPressureInput(
        symbol=symbol,
        observation_date=DAY,
        ownership=ownership,
        liquidity=liquidity,
        ownership_change_20d=Decimal(ownership_change),
        distribution_breadth_20d=Decimal(distribution),
        down_volume_ratio_20d=Decimal(down_volume),
        return_20d=Decimal(return20),
        data_quality_state=quality,
    )


def test_cross_sectional_profiles_are_explainable_and_trade_authority_remains_none():
    profiles = build_pressure_profiles(
        {
            "LOW": item("LOW", fund_ratio="0.05", top3="0.30", hhi="0.15", normal="1", stress="2",
                        ownership_change="0.01", distribution="0.10", down_volume="0.30", return20="0.05"),
            "MID": item("MID", fund_ratio="0.15", top3="0.60", hhi="0.35", normal="5", stress="8",
                        ownership_change="-0.02", distribution="0.40", down_volume="0.60", return20="-0.03"),
            "HIGH": item("HIGH", fund_ratio="0.30", top3="0.90", hhi="0.70", normal="20", stress="35",
                         ownership_change="-0.08", distribution="0.80", down_volume="0.90", return20="-0.12"),
        },
        min_universe_size=3,
    )
    assert profiles["HIGH"].fund_concentration_risk.score > profiles["LOW"].fund_concentration_risk.score
    assert profiles["HIGH"].exit_difficulty_risk.score > profiles["LOW"].exit_difficulty_risk.score
    assert profiles["HIGH"].active_selling_pressure.score > profiles["LOW"].active_selling_pressure.score
    assert profiles["HIGH"].automatic_trade_authority == "NONE"
    assert profiles["HIGH"].active_selling_pressure.components


def test_insufficient_universe_and_invalid_data_do_not_fabricate_scores():
    one = item("ONE", fund_ratio="0.1", top3="0.5", hhi="0.3", normal="2", stress="3",
               ownership_change="0", distribution="0.2", down_volume="0.4", return20="0")
    profiles = build_pressure_profiles({"ONE": one}, min_universe_size=30)
    assert profiles["ONE"].fund_concentration_risk.status is PressureScoreStatus.INSUFFICIENT_UNIVERSE

    bad = item("BAD", fund_ratio="0.1", top3="0.5", hhi="0.3", normal="2", stress="3",
               ownership_change="0", distribution="0.2", down_volume="0.4", return20="0",
               quality=DataQualityState.INVALID)
    profiles = build_pressure_profiles({"BAD": bad}, min_universe_size=1)
    assert profiles["BAD"].active_selling_pressure.status is PressureScoreStatus.INSUFFICIENT_UNIVERSE
