import math

from app.analysis.financial_intelligence_holding_model_contract import (
    HOLDING_COMPONENTS,
    HOLDING_REQUIRED_METRICS,
)
from app.analysis.financial_intelligence_holding_scoring_engine import (
    score_holding_model,
)


def _strong_payload():
    return {
        "NAV_QUALITY": {
            "nav_per_share": 1.2,
            "price_to_nav_ratio": 0.75,
        },
        "SUBSIDIARY_QUALITY": {
            "listed_subsidiary_value_share": 75.0,
            "subsidiary_dividend_coverage": 1.8,
        },
        "HOLDING_LEVERAGE": {
            "net_debt_to_nav": 5.0,
            "interest_coverage_ratio": 5.0,
        },
        "CASH_FLOW_QUALITY": {
            "holding_operating_cash_flow": 1.2,
            "dividend_income_to_financing_cost": 2.2,
        },
        "PROFITABILITY": {
            "roe": 22.0,
            "roa": 9.0,
        },
        "GROWTH_QUALITY": {
            "nav_growth": 25.0,
            "net_income_growth": 35.0,
            "dividend_income_growth": 30.0,
        },
    }


def _weak_payload():
    return {
        "NAV_QUALITY": {
            "nav_per_share": 0.0,
            "price_to_nav_ratio": 1.40,
        },
        "SUBSIDIARY_QUALITY": {
            "listed_subsidiary_value_share": 10.0,
            "subsidiary_dividend_coverage": 0.2,
        },
        "HOLDING_LEVERAGE": {
            "net_debt_to_nav": 60.0,
            "interest_coverage_ratio": 0.5,
        },
        "CASH_FLOW_QUALITY": {
            "holding_operating_cash_flow": -0.5,
            "dividend_income_to_financing_cost": 0.2,
        },
        "PROFITABILITY": {
            "roe": 1.0,
            "roa": 0.2,
        },
        "GROWTH_QUALITY": {
            "nav_growth": -20.0,
            "net_income_growth": -30.0,
            "dividend_income_growth": -25.0,
        },
    }


def test_strong_holding_scores_high():
    result = score_holding_model(
        _strong_payload()
    )

    assert result.status == "PASS"
    assert result.blocker is None
    assert result.total_score is not None
    assert result.total_score >= 95.0

    assert set(
        result.component_scores
    ) == set(HOLDING_COMPONENTS)


def test_weak_holding_scores_low():
    result = score_holding_model(
        _weak_payload()
    )

    assert result.status == "PASS"
    assert result.total_score is not None
    assert result.total_score <= 5.0


def test_missing_metric_blocks_scoring():
    payload = _strong_payload()
    payload[
        "NAV_QUALITY"
    ]["price_to_nav_ratio"] = None

    result = score_holding_model(payload)

    assert result.status == "BLOCKED"
    assert result.total_score is None
    assert (
        "NAV_QUALITY.price_to_nav_ratio"
        in result.blocker
    )


def test_score_is_deterministic():
    payload = _strong_payload()

    first = score_holding_model(payload)
    second = score_holding_model(payload)

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
        "nav_per_share",
        "price_to_nav_ratio",
        "listed_subsidiary_value_share",
        "subsidiary_dividend_coverage",
        "net_debt_to_nav",
        "interest_coverage_ratio",
        "holding_operating_cash_flow",
        "dividend_income_to_financing_cost",
        "roe",
        "roa",
        "nav_growth",
        "net_income_growth",
        "dividend_income_growth",
    }

    contracted = {
        metric
        for component in HOLDING_COMPONENTS
        for metric in HOLDING_REQUIRED_METRICS[
            component
        ]
    }

    assert contracted == covered
