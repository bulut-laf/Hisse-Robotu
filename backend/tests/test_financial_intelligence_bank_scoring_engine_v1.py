import math

from app.analysis.financial_intelligence_bank_model_contract import (
    BANK_COMPONENTS,
    BANK_REQUIRED_METRICS,
)
from app.analysis.financial_intelligence_bank_scoring_engine import (
    score_bank_model,
)


def _strong_payload():
    return {
        "CAPITAL_ADEQUACY": {
            "capital_adequacy_ratio": 20.0,
            "tier1_capital_ratio": 16.0,
        },
        "ASSET_QUALITY": {
            "npl_ratio": 1.5,
            "npl_coverage_ratio": 110.0,
        },
        "PROFITABILITY": {
            "roe": 27.0,
            "roa": 3.2,
            "net_interest_margin": 6.2,
        },
        "FUNDING_LIQUIDITY": {
            "loan_to_deposit_ratio": 90.0,
            "liquidity_ratio": 135.0,
        },
        "EFFICIENCY": {
            "cost_to_income_ratio": 30.0,
        },
        "GROWTH_QUALITY": {
            "loan_growth": 18.0,
            "deposit_growth": 17.0,
            "net_income_growth": 28.0,
        },
    }


def _weak_payload():
    return {
        "CAPITAL_ADEQUACY": {
            "capital_adequacy_ratio": 9.0,
            "tier1_capital_ratio": 7.0,
        },
        "ASSET_QUALITY": {
            "npl_ratio": 9.0,
            "npl_coverage_ratio": 40.0,
        },
        "PROFITABILITY": {
            "roe": 2.0,
            "roa": 0.2,
            "net_interest_margin": 1.0,
        },
        "FUNDING_LIQUIDITY": {
            "loan_to_deposit_ratio": 150.0,
            "liquidity_ratio": 70.0,
        },
        "EFFICIENCY": {
            "cost_to_income_ratio": 80.0,
        },
        "GROWTH_QUALITY": {
            "loan_growth": 55.0,
            "deposit_growth": 10.0,
            "net_income_growth": -20.0,
        },
    }


def test_strong_bank_scores_high():
    result = score_bank_model(_strong_payload())

    assert result.status == "PASS"
    assert result.blocker is None
    assert result.total_score is not None
    assert result.total_score >= 95.0

    assert set(result.component_scores) == set(
        BANK_COMPONENTS
    )


def test_weak_bank_scores_low():
    result = score_bank_model(_weak_payload())

    assert result.status == "PASS"
    assert result.total_score is not None
    assert result.total_score <= 5.0


def test_missing_metric_blocks_scoring():
    payload = _strong_payload()
    payload["PROFITABILITY"]["roe"] = None

    result = score_bank_model(payload)

    assert result.status == "BLOCKED"
    assert result.total_score is None
    assert "PROFITABILITY.roe" in result.blocker


def test_score_is_deterministic():
    payload = _strong_payload()

    first = score_bank_model(payload)
    second = score_bank_model(payload)

    assert math.isclose(
        first.total_score,
        second.total_score,
    )
    assert first.component_scores == second.component_scores
    assert first.metric_scores == second.metric_scores


def test_contract_metrics_are_all_accounted_for():
    covered = {
        "capital_adequacy_ratio",
        "tier1_capital_ratio",
        "npl_ratio",
        "npl_coverage_ratio",
        "roe",
        "roa",
        "net_interest_margin",
        "loan_to_deposit_ratio",
        "liquidity_ratio",
        "cost_to_income_ratio",
        "loan_growth",
        "deposit_growth",
        "net_income_growth",
    }

    contracted = {
        metric
        for component in BANK_COMPONENTS
        for metric in BANK_REQUIRED_METRICS[component]
    }

    assert contracted == covered
