from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Sequence


START_TOLERANCE_DAYS = 7
LATEST_FRESHNESS_DAYS = 7
F3_NAV_RECOVERY_VERSION = "erste-hungary-f3-nav-recovery-v1"


@dataclass(frozen=True)
class QualifiedMaxDrawdown:
    value: Decimal | None
    reason: str
    latest_date: date | None
    target_start_date: date | None
    start_observation_date: date | None
    start_lag_days: int | None
    freshness_days: int | None
    window_points: int


def _shift_year(value: datetime) -> datetime:
    try:
        return value.replace(year=value.year - 1)
    except ValueError:
        return value.replace(year=value.year - 1, day=28)


def _observation_on_or_before(
    points: Sequence[tuple[datetime, Decimal]],
    target: datetime,
) -> tuple[datetime, Decimal] | None:
    result = None
    for dt, nav in points:
        if dt <= target:
            result = (dt, nav)
        else:
            break
    return result


def qualified_max_drawdown_1y(
    points: Sequence[tuple[datetime, Decimal]],
    *,
    reference_date: date,
    start_tolerance_days: int = START_TOLERANCE_DAYS,
    latest_freshness_days: int = LATEST_FRESHNESS_DAYS,
) -> QualifiedMaxDrawdown:
    if len(points) < 2:
        return QualifiedMaxDrawdown(
            value=None,
            reason="INSUFFICIENT_POINTS",
            latest_date=None,
            target_start_date=None,
            start_observation_date=None,
            start_lag_days=None,
            freshness_days=None,
            window_points=0,
        )

    ordered = sorted(points, key=lambda item: item[0])
    latest_dt = ordered[-1][0]
    freshness_days = (reference_date - latest_dt.date()).days

    if freshness_days < 0:
        return QualifiedMaxDrawdown(
            value=None,
            reason="FUTURE_LATEST_OBSERVATION",
            latest_date=latest_dt.date(),
            target_start_date=None,
            start_observation_date=None,
            start_lag_days=None,
            freshness_days=freshness_days,
            window_points=0,
        )

    if freshness_days > latest_freshness_days:
        return QualifiedMaxDrawdown(
            value=None,
            reason="STALE_LATEST_OBSERVATION",
            latest_date=latest_dt.date(),
            target_start_date=None,
            start_observation_date=None,
            start_lag_days=None,
            freshness_days=freshness_days,
            window_points=0,
        )

    target_start = _shift_year(latest_dt)
    start_obs = _observation_on_or_before(ordered, target_start)

    if start_obs is None:
        return QualifiedMaxDrawdown(
            value=None,
            reason="NO_OBSERVATION_ON_OR_BEFORE_1Y_START",
            latest_date=latest_dt.date(),
            target_start_date=target_start.date(),
            start_observation_date=None,
            start_lag_days=None,
            freshness_days=freshness_days,
            window_points=0,
        )

    start_dt, _ = start_obs
    lag_days = (target_start.date() - start_dt.date()).days

    if lag_days > start_tolerance_days:
        return QualifiedMaxDrawdown(
            value=None,
            reason="STALE_START_OBSERVATION",
            latest_date=latest_dt.date(),
            target_start_date=target_start.date(),
            start_observation_date=start_dt.date(),
            start_lag_days=lag_days,
            freshness_days=freshness_days,
            window_points=0,
        )

    window = [
        (dt, nav)
        for dt, nav in ordered
        if start_dt <= dt <= latest_dt
    ]

    if len(window) < 2:
        return QualifiedMaxDrawdown(
            value=None,
            reason="INSUFFICIENT_WINDOW_POINTS",
            latest_date=latest_dt.date(),
            target_start_date=target_start.date(),
            start_observation_date=start_dt.date(),
            start_lag_days=lag_days,
            freshness_days=freshness_days,
            window_points=len(window),
        )

    peak = window[0][1]
    worst = Decimal("0")

    for _, nav in window:
        if nav > peak:
            peak = nav

        if peak == 0:
            continue

        drawdown = (nav / peak) - Decimal("1")
        if drawdown < worst:
            worst = drawdown

    return QualifiedMaxDrawdown(
        value=worst,
        reason="QUALIFIED",
        latest_date=latest_dt.date(),
        target_start_date=target_start.date(),
        start_observation_date=start_dt.date(),
        start_lag_days=lag_days,
        freshness_days=freshness_days,
        window_points=len(window),
    )