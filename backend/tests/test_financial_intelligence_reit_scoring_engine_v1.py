import math

from app.analysis.financial_intelligence_reit_model_contract import (
    REIT_COMPONENTS,
    REIT_REQUIRED_METRICS,
)
from app.analysis.financial_intelligence_reit_scoring_engine import (
    score_reit_model,
)


def _strong_payload():
    return {
        "PORTFOLIO_QUALITY": {
            "occupancy_rate": 97.0,
            "rental_income_margin": 70.0,
        },
        "LEVERAGE": {
            "net_debt_to_assets": 15.0,
            "interest_coverage_ratio": 5.0,
        },
        "NAV_VALUATION": {
            "nav_per_share": 1.2,
            "price_to_nav_ratio": 0.80,
        },
        "PROFITABILITY": {
            "roe": 20.0,
            "roa": 9.0,
            "ffo_margin": 50.0,
        },
        "CASH_DISTRIBUTION": {
            "ffo_payout_ratio": 60.0,
            "operating_cash_flow_to_dividend": 1.7,
        },
        "GROWTH_QUALITY": {
            "rental_income_growth": 20.0,
            "ffo_growth": 30.0,
            "nav_growth": 25.0,
        },
    }


def _weak_payload():
    return {
        "PORTFOLIO_QUALITY": {
            "occupancy_rate": 60.0,
            "rental_income_margin": 20.0,
        },
        "LEVERAGE": {
            "net_debt_to_assets": 70.0,
            "interest_coverage_ratio": 0.5,
        },
        "NAV_VALUATION": {
            "nav_per_share": 0.0,
            "price_to_nav_ratio": 1.50,
        },
        "PROFITABILITY": {
            "roe": 0.0,
            "roa": 0.0,
            "ffo_margin": 5.0,
        },
        "CASH_DISTRIBUTION": {
            "ffo_payout_ratio": 120.0,
            "operating_cash_flow_to_dividend": 0.4,
        },
        "GROWTH_QUALITY": {
            "rental_income_growth": -20.0,
            "ffo_growth": -30.0,
            "nav_growth": -20.0,
        },
    }


def test_strong_reit_scores_high():
    result = score_reit_model(
        _strong_payload()
    )

    assert result.status == "PASS"
    assert result.blocker is None
    assert result.total_score is not None
    assert result.total_score >= 95.0

    assert set(
        result.component_scores
    ) == set(REIT_COMPONENTS)


def test_weak_reit_scores_low():
    result = score_reit_model(
        _weak_payload()
    )

    assert result.status == "PASS"
    assert result.total_score is not None
    assert result.total_score <= 5.0


def test_missing_metric_blocks_scoring():
    payload = _strong_payload()
    payload[
        "PORTFOLIO_QUALITY"
    ]["occupancy_rate"] = None

    result = score_reit_model(payload)

    assert result.status == "BLOCKED"
    assert result.total_score is None
    assert (
        "PORTFOLIO_QUALITY.occupancy_rate"
        in result.blocker
    )


def test_score_is_deterministic():
    payload = _strong_payload()

    first = score_reit_model(payload)
    second = score_reit_model(payload)

    assert math.isclose(
        first.total_score,
        second.total_score,
    )

    assert (
        first.component_scores
        == second.component_scores
    )

    assert (
        first.metric_scores
        == second.metric_scores
    )


def test_contract_metrics_are_all_accounted_for():
    covered = {
        "occupancy_rate",
        "rental_income_margin",
        "net_debt_to_assets",
        "interest_coverage_ratio",
        "nav_per_share",
        "price_to_nav_ratio",
        "roe",
        "roa",
        "ffo_margin",
        "ffo_payout_ratio",
        "operating_cash_flow_to_dividend",
        "rental_income_growth",
        "ffo_growth",
        "nav_growth",
    }

    contracted = {
        metric
        for component in REIT_COMPONENTS
        for metric in REIT_REQUIRED_METRICS[
            component
        ]
    }

    assert contracted == covered
