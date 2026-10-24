import math

from app.analysis.financial_intelligence_insurance_model_contract import (
    INSURANCE_COMPONENTS,
    INSURANCE_REQUIRED_METRICS,
)
from app.analysis.financial_intelligence_insurance_scoring_engine import (
    score_insurance_model,
)


def _strong_payload():
    return {
        "SOLVENCY_CAPITAL": {
            "solvency_ratio": 190.0,
            "equity_to_assets_ratio": 22.0,
        },
        "UNDERWRITING_QUALITY": {
            "loss_ratio": 50.0,
            "expense_ratio": 22.0,
            "combined_ratio": 88.0,
        },
        "RESERVE_ADEQUACY": {
            "technical_reserve_coverage": 145.0,
            "claims_reserve_growth": 15.0,
        },
        "PROFITABILITY": {
            "roe": 28.0,
            "roa": 3.2,
            "underwriting_margin": 18.0,
        },
        "LIQUIDITY_INVESTMENT": {
            "liquidity_ratio": 135.0,
            "investment_yield": 16.0,
        },
        "GROWTH_QUALITY": {
            "premium_growth": 25.0,
            "net_income_growth": 35.0,
        },
    }


def _weak_payload():
    return {
        "SOLVENCY_CAPITAL": {
            "solvency_ratio": 90.0,
            "equity_to_assets_ratio": 5.0,
        },
        "UNDERWRITING_QUALITY": {
            "loss_ratio": 90.0,
            "expense_ratio": 50.0,
            "combined_ratio": 115.0,
        },
        "RESERVE_ADEQUACY": {
            "technical_reserve_coverage": 90.0,
            "claims_reserve_growth": 60.0,
        },
        "PROFITABILITY": {
            "roe": 2.0,
            "roa": 0.1,
            "underwriting_margin": -10.0,
        },
        "LIQUIDITY_INVESTMENT": {
            "liquidity_ratio": 70.0,
            "investment_yield": -2.0,
        },
        "GROWTH_QUALITY": {
            "premium_growth": 70.0,
            "net_income_growth": -30.0,
        },
    }


def test_strong_insurer_scores_high():
    result = score_insurance_model(
        _strong_payload()
    )

    assert result.status == "PASS"
    assert result.blocker is None
    assert result.total_score is not None
    assert result.total_score >= 95.0

    assert set(result.component_scores) == set(
        INSURANCE_COMPONENTS
    )


def test_weak_insurer_scores_low():
    result = score_insurance_model(
        _weak_payload()
    )

    assert result.status == "PASS"
    assert result.total_score is not None
    assert result.total_score <= 5.0


def test_missing_metric_blocks_scoring():
    payload = _strong_payload()
    payload[
        "UNDERWRITING_QUALITY"
    ]["combined_ratio"] = None

    result = score_insurance_model(payload)

    assert result.status == "BLOCKED"
    assert result.total_score is None
    assert (
        "UNDERWRITING_QUALITY.combined_ratio"
        in result.blocker
    )


def test_score_is_deterministic():
    payload = _strong_payload()

    first = score_insurance_model(payload)
    second = score_insurance_model(payload)

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
        "solvency_ratio",
        "equity_to_assets_ratio",
        "loss_ratio",
        "expense_ratio",
        "combined_ratio",
        "technical_reserve_coverage",
        "claims_reserve_growth",
        "roe",
        "roa",
        "underwriting_margin",
        "liquidity_ratio",
        "investment_yield",
        "premium_growth",
        "net_income_growth",
    }

    contracted = {
        metric
        for component in INSURANCE_COMPONENTS
        for metric in INSURANCE_REQUIRED_METRICS[
            component
        ]
    }

    assert contracted == covered
