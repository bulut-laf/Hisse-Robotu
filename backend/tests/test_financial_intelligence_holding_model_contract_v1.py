import math
import pytest

from app.analysis.financial_intelligence_holding_model_contract import (
    HOLDING_COMPONENTS,
    HOLDING_COMPONENT_WEIGHTS,
    HOLDING_REQUIRED_METRICS,
    assert_holding_model_input_ready,
    holding_component_weight,
    validate_holding_model_input,
)


def _complete_payload():
    return {
        component: {
            metric: 1.0
            for metric in HOLDING_REQUIRED_METRICS[component]
        }
        for component in HOLDING_COMPONENTS
    }


def test_holding_component_contract_is_complete():
    assert HOLDING_COMPONENTS == (
        "NAV_QUALITY",
        "SUBSIDIARY_QUALITY",
        "HOLDING_LEVERAGE",
        "CASH_FLOW_QUALITY",
        "PROFITABILITY",
        "GROWTH_QUALITY",
    )

    assert set(HOLDING_COMPONENT_WEIGHTS) == set(
        HOLDING_COMPONENTS
    )

    assert math.isclose(
        sum(HOLDING_COMPONENT_WEIGHTS.values()),
        1.0,
    )


def test_complete_holding_payload_is_ready():
    payload = _complete_payload()

    result = validate_holding_model_input(payload)

    assert result.status == "PASS"
    assert result.ready_for_scoring is True
    assert result.blocker is None

    assert_holding_model_input_ready(payload)


def test_missing_component_fails_closed():
    payload = _complete_payload()
    payload.pop("HOLDING_LEVERAGE")

    result = validate_holding_model_input(payload)

    assert result.status == "BLOCKED"
    assert result.ready_for_scoring is False
    assert (
        "HOLDING_LEVERAGE"
        in result.missing_components
    )


def test_missing_metric_fails_closed_and_never_zero():
    payload = _complete_payload()
    payload[
        "NAV_QUALITY"
    ]["price_to_nav_ratio"] = None

    result = validate_holding_model_input(payload)

    assert result.status == "BLOCKED"
    assert result.ready_for_scoring is False
    assert (
        "NAV_QUALITY.price_to_nav_ratio"
        in result.missing_metrics
    )

    with pytest.raises(
        ValueError,
        match="NAV_QUALITY.price_to_nav_ratio",
    ):
        assert_holding_model_input_ready(payload)


def test_unknown_component_weight_is_rejected():
    assert (
        holding_component_weight("nav_quality")
        == 0.25
    )

    with pytest.raises(
        KeyError,
        match="UNKNOWN_HOLDING_COMPONENT",
    ):
        holding_component_weight(
            "INDUSTRIAL_HEALTH"
        )
