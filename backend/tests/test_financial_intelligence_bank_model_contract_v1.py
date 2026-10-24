import math
import pytest

from app.analysis.financial_intelligence_bank_model_contract import (
    BANK_COMPONENTS,
    BANK_COMPONENT_WEIGHTS,
    BANK_REQUIRED_METRICS,
    assert_bank_model_input_ready,
    bank_component_weight,
    validate_bank_model_input,
)


def _complete_payload():
    return {
        component: {
            metric: 1.0
            for metric in BANK_REQUIRED_METRICS[component]
        }
        for component in BANK_COMPONENTS
    }


def test_bank_component_contract_is_complete():
    assert BANK_COMPONENTS == (
        "CAPITAL_ADEQUACY",
        "ASSET_QUALITY",
        "PROFITABILITY",
        "FUNDING_LIQUIDITY",
        "EFFICIENCY",
        "GROWTH_QUALITY",
    )

    assert set(BANK_COMPONENT_WEIGHTS) == set(BANK_COMPONENTS)
    assert math.isclose(sum(BANK_COMPONENT_WEIGHTS.values()), 1.0)


def test_complete_bank_payload_is_ready_for_scoring():
    payload = _complete_payload()

    result = validate_bank_model_input(payload)

    assert result.status == "PASS"
    assert result.ready_for_scoring is True
    assert result.blocker is None

    assert_bank_model_input_ready(payload)


def test_missing_component_fails_closed():
    payload = _complete_payload()
    payload.pop("ASSET_QUALITY")

    result = validate_bank_model_input(payload)

    assert result.status == "BLOCKED"
    assert result.ready_for_scoring is False
    assert "ASSET_QUALITY" in result.missing_components
    assert "MISSING_COMPONENTS:ASSET_QUALITY" in result.blocker


def test_missing_metric_fails_closed_and_never_maps_to_zero():
    payload = _complete_payload()
    payload["PROFITABILITY"]["roe"] = None

    result = validate_bank_model_input(payload)

    assert result.status == "BLOCKED"
    assert result.ready_for_scoring is False
    assert "PROFITABILITY.roe" in result.missing_metrics

    with pytest.raises(ValueError, match="PROFITABILITY.roe"):
        assert_bank_model_input_ready(payload)


def test_unknown_component_weight_is_rejected():
    assert bank_component_weight("capital_adequacy") == 0.20

    with pytest.raises(
        KeyError,
        match="UNKNOWN_BANK_COMPONENT",
    ):
        bank_component_weight("INDUSTRIAL_HEALTH")
