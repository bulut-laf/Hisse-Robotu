from datetime import datetime, timezone
from decimal import Decimal

from backend.app.funds.international.erste_hungary_f2_bridge import (
    MAX_TARGET_LAG_DAYS,
    build_f1_f2_f3_input,
    derive_f2_returns,
    observation_on_or_before,
    shift_months,
)


def test_shift_months_clamps_end_of_month():
    value = datetime(2026, 3, 31, tzinfo=timezone.utc)
    assert shift_months(value, 1).date().isoformat() == "2026-02-28"


def test_observation_uses_last_point_on_or_before_target():
    points = [
        (datetime(2026, 1, 1, tzinfo=timezone.utc), Decimal("10")),
        (datetime(2026, 1, 3, tzinfo=timezone.utc), Decimal("11")),
    ]
    target = datetime(2026, 1, 4, tzinfo=timezone.utc)

    result = observation_on_or_before(points, target)

    assert result is not None
    assert result[0].date().isoformat() == "2026-01-03"
    assert result[1] == Decimal("11")


def test_observation_rejects_stale_nav():
    points = [
        (datetime(2026, 4, 30, tzinfo=timezone.utc), Decimal("12")),
    ]
    target = datetime(2026, 6, 30, tzinfo=timezone.utc)

    assert observation_on_or_before(points, target) is None


def test_observation_accepts_gap_within_guard():
    points = [
        (datetime(2026, 3, 23, tzinfo=timezone.utc), Decimal("10")),
    ]
    target = datetime(2026, 3, 24, tzinfo=timezone.utc)

    result = observation_on_or_before(points, target)

    assert result is not None
    assert result[1] == Decimal("10")


def test_derive_f2_returns_requires_real_history_near_target_date():
    points = [
        (datetime(2026, 1, 31, tzinfo=timezone.utc), Decimal("10")),
        (datetime(2026, 4, 30, tzinfo=timezone.utc), Decimal("12")),
        (datetime(2026, 7, 31, tzinfo=timezone.utc), Decimal("15")),
    ]

    r1, r3, r6 = derive_f2_returns(points)

    assert r1 is None
    assert r3 == Decimal("0.25")
    assert r6 == Decimal("0.5")


def test_default_lag_guard_is_seven_calendar_days():
    assert MAX_TARGET_LAG_DAYS == 7


def test_build_input_preserves_f2_fields():
    value = build_f1_f2_f3_input(
        isin="HU0000000001",
        category_id="EQUITY",
        category_rank_percentile=Decimal("0.8"),
        category_rank_change=3,
        return_1m=Decimal("0.01"),
        return_3m=Decimal("0.02"),
        return_6m=Decimal("0.03"),
        volatility_percentile=Decimal("0.4"),
        max_drawdown_1y=Decimal("-0.08"),
    )

    assert value.return_1m == Decimal("0.01")
    assert value.return_3m == Decimal("0.02")
    assert value.return_6m == Decimal("0.03")