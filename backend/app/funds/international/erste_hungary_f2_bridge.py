from __future__ import annotations

from calendar import monthrange
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from backend.app.funds.evidence_mapper import FundEvidenceInput


F2_BRIDGE_VERSION = "erste-hungary-f2-evidence-bridge-v1"
MAX_TARGET_LAG_DAYS = 7


def shift_months(value: datetime, months: int) -> datetime:
    year = value.year
    month = value.month - months
    while month <= 0:
        year -= 1
        month += 12
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def observation_on_or_before(
    points: Sequence[tuple[datetime, Decimal]],
    target: datetime,
    *,
    max_lag_days: int = MAX_TARGET_LAG_DAYS,
) -> tuple[datetime, Decimal] | None:
    result = None
    for dt, price in points:
        if dt <= target:
            result = (dt, price)
        else:
            break

    if result is None:
        return None

    observation_dt, _ = result
    lag_days = (target.date() - observation_dt.date()).days

    if lag_days < 0 or lag_days > max_lag_days:
        return None

    return result


def trailing_return(
    points: Sequence[tuple[datetime, Decimal]],
    months: int,
    *,
    max_lag_days: int = MAX_TARGET_LAG_DAYS,
) -> Decimal | None:
    if not points:
        return None

    latest_dt, latest_price = points[-1]
    old = observation_on_or_before(
        points,
        shift_months(latest_dt, months),
        max_lag_days=max_lag_days,
    )

    if old is None:
        return None

    _, old_price = old
    if old_price == 0:
        return None

    return (latest_price / old_price) - Decimal("1")


def derive_f2_returns(
    points: Sequence[tuple[datetime, Decimal]],
    *,
    max_lag_days: int = MAX_TARGET_LAG_DAYS,
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    return (
        trailing_return(points, 1, max_lag_days=max_lag_days),
        trailing_return(points, 3, max_lag_days=max_lag_days),
        trailing_return(points, 6, max_lag_days=max_lag_days),
    )


def build_f1_f2_f3_input(
    *,
    isin: str,
    category_id: str,
    category_rank_percentile: Decimal | None,
    category_rank_change: int | None,
    return_1m: Decimal | None,
    return_3m: Decimal | None,
    return_6m: Decimal | None,
    volatility_percentile: Decimal | None,
    max_drawdown_1y: Decimal | None,
) -> FundEvidenceInput:
    return FundEvidenceInput(
        canonical_fund_id=f"fund:isin:{isin.strip().upper()}",
        category_id=category_id,
        category_rank_percentile=category_rank_percentile,
        category_rank_change=category_rank_change,
        return_1m=return_1m,
        return_3m=return_3m,
        return_6m=return_6m,
        volatility_percentile=volatility_percentile,
        max_drawdown=max_drawdown_1y,
        fund_size_change=None,
        investor_change=None,
        net_flow_ratio=None,
        total_expense_ratio=None,
        regime_fit=None,
        allocation_known=False,
    )