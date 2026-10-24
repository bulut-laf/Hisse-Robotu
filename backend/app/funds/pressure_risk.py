from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from statistics import median
from typing import Mapping

from .contracts import DataQualityState


class PressureScoreStatus(str, Enum):
    READY = "READY"
    NOT_COMPUTABLE = "NOT_COMPUTABLE"
    INSUFFICIENT_UNIVERSE = "INSUFFICIENT_UNIVERSE"


@dataclass(frozen=True, slots=True)
class FundOwnershipConcentration:
    fund_owned_shares: Decimal | None
    free_float_shares: Decimal | None
    fund_free_float_ratio: Decimal | None
    largest_fund_share: Decimal | None
    top3_fund_share: Decimal | None
    top5_fund_share: Decimal | None
    hhi: Decimal | None


@dataclass(frozen=True, slots=True)
class FundExitLiquidity:
    total_fund_position_value: Decimal | None
    adv20_value: Decimal | None
    median_daily_value_20: Decimal | None
    stressed_liquidity_capacity: Decimal | None
    liquidation_days_normal: Decimal | None
    liquidation_days_aggressive: Decimal | None
    liquidation_days_stress: Decimal | None


@dataclass(frozen=True, slots=True)
class StockFundPressureInput:
    symbol: str
    observation_date: date
    ownership: FundOwnershipConcentration
    liquidity: FundExitLiquidity
    ownership_change_20d: Decimal | None
    distribution_breadth_20d: Decimal | None
    down_volume_ratio_20d: Decimal | None
    return_20d: Decimal | None
    data_quality_state: DataQualityState = DataQualityState.VALID


@dataclass(frozen=True, slots=True)
class PressureSubScore:
    score: Decimal | None
    status: PressureScoreStatus
    components: tuple[tuple[str, Decimal], ...]


@dataclass(frozen=True, slots=True)
class StockFundPressureProfile:
    symbol: str
    observation_date: date
    fund_concentration_risk: PressureSubScore
    exit_difficulty_risk: PressureSubScore
    active_selling_pressure: PressureSubScore
    data_quality_state: DataQualityState
    automatic_trade_authority: str = "NONE"


def _finite_non_negative(value: Decimal, name: str) -> Decimal:
    if not value.is_finite() or value < 0:
        raise ValueError(f"{name} negatif veya sonlu olmayan değer olamaz.")
    return value


def calculate_fund_free_float_ratio(
    fund_owned_shares: Decimal | None,
    free_float_shares: Decimal | None,
) -> Decimal | None:
    if fund_owned_shares is None or free_float_shares is None:
        return None
    _finite_non_negative(fund_owned_shares, "fund_owned_shares")
    _finite_non_negative(free_float_shares, "free_float_shares")
    if free_float_shares == 0:
        return None
    return fund_owned_shares / free_float_shares


def calculate_concentration(
    fund_positions: Mapping[str, Decimal],
    *,
    free_float_shares: Decimal | None = None,
) -> FundOwnershipConcentration:
    cleaned: list[tuple[str, Decimal]] = []
    for fund_id, shares in fund_positions.items():
        identity = str(fund_id).strip()
        if not identity:
            raise ValueError("FUND_ID_EMPTY")
        cleaned.append((identity, _finite_non_negative(Decimal(shares), "fund_position")))
    cleaned.sort(key=lambda item: (-item[1], item[0]))
    total = sum((value for _, value in cleaned), Decimal("0"))
    ratios = [value / total for _, value in cleaned] if total > 0 else []
    largest = ratios[0] if ratios else None
    top3 = sum(ratios[:3], Decimal("0")) if ratios else None
    top5 = sum(ratios[:5], Decimal("0")) if ratios else None
    hhi = sum((ratio * ratio for ratio in ratios), Decimal("0")) if ratios else None
    return FundOwnershipConcentration(
        fund_owned_shares=total,
        free_float_shares=free_float_shares,
        fund_free_float_ratio=calculate_fund_free_float_ratio(total, free_float_shares),
        largest_fund_share=largest,
        top3_fund_share=top3,
        top5_fund_share=top5,
        hhi=hhi,
    )


def _liquidation_days(
    position_value: Decimal | None,
    daily_capacity: Decimal | None,
) -> Decimal | None:
    if position_value is None or daily_capacity is None:
        return None
    _finite_non_negative(position_value, "position_value")
    _finite_non_negative(daily_capacity, "daily_capacity")
    if daily_capacity == 0:
        return None
    return position_value / daily_capacity


def calculate_exit_liquidity(
    total_fund_position_value: Decimal | None,
    adv20_value: Decimal | None,
    *,
    median_daily_value_20: Decimal | None = None,
    stressed_liquidity_capacity: Decimal | None = None,
) -> FundExitLiquidity:
    normal_capacity = None if adv20_value is None else adv20_value * Decimal("0.10")
    aggressive_capacity = None if adv20_value is None else adv20_value * Decimal("0.20")
    return FundExitLiquidity(
        total_fund_position_value=total_fund_position_value,
        adv20_value=adv20_value,
        median_daily_value_20=median_daily_value_20,
        stressed_liquidity_capacity=stressed_liquidity_capacity,
        liquidation_days_normal=_liquidation_days(total_fund_position_value, normal_capacity),
        liquidation_days_aggressive=_liquidation_days(total_fund_position_value, aggressive_capacity),
        liquidation_days_stress=_liquidation_days(total_fund_position_value, stressed_liquidity_capacity),
    )


def percentile_map(values: Mapping[str, Decimal]) -> dict[str, Decimal]:
    if not values:
        return {}
    ranked = sorted((value, key) for key, value in values.items())
    count = len(ranked)
    if count == 1:
        return {ranked[0][1]: Decimal("0.50")}
    output: dict[str, Decimal] = {}
    index = 0
    while index < count:
        value = ranked[index][0]
        end = index + 1
        while end < count and ranked[end][0] == value:
            end += 1
        average_rank = (Decimal(index) + Decimal(end - 1)) / Decimal("2")
        percentile = average_rank / Decimal(count - 1)
        for position in range(index, end):
            output[ranked[position][1]] = percentile
        index = end
    return output


def _score_from_components(
    symbol: str,
    component_percentiles: Mapping[str, Mapping[str, Decimal]],
    *,
    minimum_components: int,
) -> PressureSubScore:
    values: list[tuple[str, Decimal]] = []
    for name in sorted(component_percentiles):
        value = component_percentiles[name].get(symbol)
        if value is not None:
            values.append((name, value))
    if len(values) < minimum_components:
        return PressureSubScore(None, PressureScoreStatus.NOT_COMPUTABLE, tuple(values))
    score = Decimal(str(median([value for _, value in values]))) * Decimal("100")
    return PressureSubScore(score, PressureScoreStatus.READY, tuple(values))


def build_pressure_profiles(
    inputs: Mapping[str, StockFundPressureInput],
    *,
    min_universe_size: int = 30,
) -> dict[str, StockFundPressureProfile]:
    if min_universe_size < 1:
        raise ValueError("min_universe_size en az 1 olmalıdır.")

    eligible = {
        symbol: item
        for symbol, item in inputs.items()
        if item.data_quality_state in (DataQualityState.VALID, DataQualityState.PARTIAL)
    }
    if len(eligible) < min_universe_size:
        unavailable = PressureSubScore(None, PressureScoreStatus.INSUFFICIENT_UNIVERSE, ())
        return {
            symbol: StockFundPressureProfile(
                symbol=item.symbol,
                observation_date=item.observation_date,
                fund_concentration_risk=unavailable,
                exit_difficulty_risk=unavailable,
                active_selling_pressure=unavailable,
                data_quality_state=item.data_quality_state,
            )
            for symbol, item in sorted(inputs.items())
        }

    concentration_raw: dict[str, dict[str, Decimal]] = {
        "fund_free_float_ratio": {},
        "top3_fund_share": {},
        "hhi": {},
    }
    exit_raw: dict[str, dict[str, Decimal]] = {
        "liquidation_days_normal": {},
        "liquidation_days_stress": {},
    }
    selling_raw: dict[str, dict[str, Decimal]] = {
        "ownership_decline_20d": {},
        "distribution_breadth_20d": {},
        "down_volume_ratio_20d": {},
        "negative_return_20d": {},
    }

    for symbol, item in eligible.items():
        ownership = item.ownership
        liquidity = item.liquidity
        if ownership.fund_free_float_ratio is not None:
            concentration_raw["fund_free_float_ratio"][symbol] = ownership.fund_free_float_ratio
        if ownership.top3_fund_share is not None:
            concentration_raw["top3_fund_share"][symbol] = ownership.top3_fund_share
        if ownership.hhi is not None:
            concentration_raw["hhi"][symbol] = ownership.hhi
        if liquidity.liquidation_days_normal is not None:
            exit_raw["liquidation_days_normal"][symbol] = liquidity.liquidation_days_normal
        if liquidity.liquidation_days_stress is not None:
            exit_raw["liquidation_days_stress"][symbol] = liquidity.liquidation_days_stress
        if item.ownership_change_20d is not None:
            selling_raw["ownership_decline_20d"][symbol] = max(-item.ownership_change_20d, Decimal("0"))
        if item.distribution_breadth_20d is not None:
            selling_raw["distribution_breadth_20d"][symbol] = item.distribution_breadth_20d
        if item.down_volume_ratio_20d is not None:
            selling_raw["down_volume_ratio_20d"][symbol] = item.down_volume_ratio_20d
        if item.return_20d is not None:
            selling_raw["negative_return_20d"][symbol] = max(-item.return_20d, Decimal("0"))

    concentration_pct = {name: percentile_map(values) for name, values in concentration_raw.items()}
    exit_pct = {name: percentile_map(values) for name, values in exit_raw.items()}
    selling_pct = {name: percentile_map(values) for name, values in selling_raw.items()}

    result: dict[str, StockFundPressureProfile] = {}
    for symbol, item in sorted(inputs.items()):
        if symbol not in eligible:
            unavailable = PressureSubScore(None, PressureScoreStatus.NOT_COMPUTABLE, ())
            result[symbol] = StockFundPressureProfile(
                symbol=item.symbol,
                observation_date=item.observation_date,
                fund_concentration_risk=unavailable,
                exit_difficulty_risk=unavailable,
                active_selling_pressure=unavailable,
                data_quality_state=item.data_quality_state,
            )
            continue
        result[symbol] = StockFundPressureProfile(
            symbol=item.symbol,
            observation_date=item.observation_date,
            fund_concentration_risk=_score_from_components(
                symbol, concentration_pct, minimum_components=2
            ),
            exit_difficulty_risk=_score_from_components(
                symbol, exit_pct, minimum_components=1
            ),
            active_selling_pressure=_score_from_components(
                symbol, selling_pct, minimum_components=2
            ),
            data_quality_state=item.data_quality_state,
        )
    return result
