from decimal import Decimal

import pytest

from backend.app.funds.risk_metrics import (
    build_f3_metrics,
    calculate_raw_risk,
)


def test_raw_risk_calculates_drawdown():
    metric = calculate_raw_risk(
        (
            Decimal("100"),
            Decimal("120"),
            Decimal("80"),
            Decimal("130"),
            Decimal("70"),
        )
    )

    assert metric is not None

    volatility, max_drawdown = metric

    assert volatility > Decimal("0")
    assert max_drawdown < Decimal("-0.40")


def test_cross_sectional_volatility_percentile():
    metrics = build_f3_metrics(
        {
            "LOW": (
                "100",
                "101",
                "102",
                "103",
                "104",
            ),
            "HIGH": (
                "100",
                "120",
                "80",
                "130",
                "70",
            ),
        }
    )

    assert (
        metrics["LOW"].volatility
        < metrics["HIGH"].volatility
    )

    assert (
        metrics["LOW"].volatility_percentile
        == Decimal("0")
    )

    assert (
        metrics["HIGH"].volatility_percentile
        == Decimal("1")
    )


def test_single_fund_percentile_is_midpoint():
    metrics = build_f3_metrics(
        {
            "ONE": (
                "100",
                "101",
                "102",
            )
        }
    )

    assert (
        metrics["ONE"].volatility_percentile
        == Decimal("0.50")
    )


def test_insufficient_history_is_not_fabricated():
    metrics = build_f3_metrics(
        {
            "SHORT": (
                "100",
                "101",
            )
        }
    )

    assert metrics == {}


def test_invalid_price_fails_closed():
    with pytest.raises(
        ValueError,
        match="F3_PRICE_MUST_BE_POSITIVE_FINITE",
    ):
        build_f3_metrics(
            {
                "BAD": (
                    "100",
                    "0",
                    "101",
                )
            }
        )
