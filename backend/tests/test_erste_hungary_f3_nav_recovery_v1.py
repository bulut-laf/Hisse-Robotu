from datetime import date, datetime, timezone
from decimal import Decimal

from backend.app.funds.international.erste_hungary_f3_nav_recovery import (
    LATEST_FRESHNESS_DAYS,
    START_TOLERANCE_DAYS,
    qualified_max_drawdown_1y,
)


def test_constants_are_seven_days():
    assert START_TOLERANCE_DAYS == 7
    assert LATEST_FRESHNESS_DAYS == 7


def test_rejects_short_history():
    points = [
        (datetime(2026, 4, 1, tzinfo=timezone.utc), Decimal("10")),
        (datetime(2026, 9, 25, tzinfo=timezone.utc), Decimal("9")),
    ]

    result = qualified_max_drawdown_1y(
        points,
        reference_date=date(2026, 9, 25),
    )

    assert result.value is None
    assert result.reason == "NO_OBSERVATION_ON_OR_BEFORE_1Y_START"


def test_rejects_stale_latest_observation():
    points = [
        (datetime(2025, 7, 24, tzinfo=timezone.utc), Decimal("10")),
        (datetime(2026, 7, 24, tzinfo=timezone.utc), Decimal("9")),
    ]

    result = qualified_max_drawdown_1y(
        points,
        reference_date=date(2026, 9, 25),
    )

    assert result.value is None
    assert result.reason == "STALE_LATEST_OBSERVATION"
    assert result.freshness_days == 63


def test_accepts_full_year_and_fresh_latest():
    points = [
        (datetime(2025, 9, 25, tzinfo=timezone.utc), Decimal("10")),
        (datetime(2026, 1, 10, tzinfo=timezone.utc), Decimal("12")),
        (datetime(2026, 5, 10, tzinfo=timezone.utc), Decimal("9")),
        (datetime(2026, 9, 25, tzinfo=timezone.utc), Decimal("11")),
    ]

    result = qualified_max_drawdown_1y(
        points,
        reference_date=date(2026, 9, 25),
    )

    assert result.reason == "QUALIFIED"
    assert result.value == Decimal("-0.25")
    assert result.freshness_days == 0


def test_accepts_start_observation_within_tolerance():
    points = [
        (datetime(2025, 9, 22, tzinfo=timezone.utc), Decimal("10")),
        (datetime(2026, 9, 25, tzinfo=timezone.utc), Decimal("11")),
    ]

    result = qualified_max_drawdown_1y(
        points,
        reference_date=date(2026, 9, 25),
    )

    assert result.reason == "QUALIFIED"
    assert result.start_lag_days == 3
    assert result.value == Decimal("0")