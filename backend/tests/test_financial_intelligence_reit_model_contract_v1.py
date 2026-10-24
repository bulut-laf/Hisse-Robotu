import math
import pytest

from app.analysis.financial_intelligence_reit_model_contract import (
    REIT_COMPONENTS,
    REIT_COMPONENT_WEIGHTS,
    REIT_REQUIRED_METRICS,
    assert_reit_model_input_ready,
    reit_component_weight,
    validate_reit_model_input,
)


def _complete_payload():
    return {
        component: {
            metric: 1.0
            for metric in REIT_REQUIRED_METRICS[component]
        }
        for component in REIT_COMPONENTS
    }


def test_reit_component_contract_is_complete():
    assert REIT_COMPONENTS == (
        "PORTFOLIO_QUALITY",
        "LEVERAGE",
        "NAV_VALUATION",
        "PROFITABILITY",
        "CASH_DISTRIBUTION",
        "GROWTH_QUALITY",
    )

    assert set(REIT_COMPONENT_WEIGHTS) == set(REIT_COMPONENTS)

    assert math.isclose(
        sum(REIT_COMPONENT_WEIGHTS.values()),
        1.0,
    )


def test_complete_reit_payload_is_ready():
    result = validate_reit_model_input(
        _complete_payload()
    )

    assert result.status == "PASS"
    assert result.ready_for_scoring is True
    assert result.blocker is None

    assert_reit_model_input_ready(
        _complete_payload()
    )


def test_missing_component_fails_closed():
    payload = _complete_payload()
    payload.pop("NAV_VALUATION")

    result = validate_reit_model_input(payload)

    assert result.status == "BLOCKED"
    assert result.ready_for_scoring is False
    assert "NAV_VALUATION" in result.missing_components


def test_missing_metric_fails_closed_and_never_zero():
    payload = _complete_payload()
    payload[
        "PORTFOLIO_QUALITY"
    ]["occupancy_rate"] = None

    result = validate_reit_model_input(payload)

    assert result.status == "BLOCKED"
    assert result.ready_for_scoring is False
    assert (
        "PORTFOLIO_QUALITY.occupancy_rate"
        in result.missing_metrics
    )

    with pytest.raises(
        ValueError,
        match="PORTFOLIO_QUALITY.occupancy_rate",
    ):
        assert_reit_model_input_ready(payload)


def test_unknown_component_weight_is_rejected():
    assert (
        reit_component_weight(
            "portfolio_quality"
        )
        == 0.20
    )

    with pytest.raises(
        KeyError,
        match="UNKNOWN_REIT_COMPONENT",
    ):
        reit_component_weight(
            "INDUSTRIAL_HEALTH"
        )
