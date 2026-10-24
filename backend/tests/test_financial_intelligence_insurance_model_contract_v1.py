import math
import pytest

from app.analysis.financial_intelligence_insurance_model_contract import (
    INSURANCE_COMPONENTS,
    INSURANCE_COMPONENT_WEIGHTS,
    INSURANCE_REQUIRED_METRICS,
    assert_insurance_model_input_ready,
    insurance_component_weight,
    validate_insurance_model_input,
)


def _complete_payload():
    return {
        component: {
            metric: 1.0
            for metric in INSURANCE_REQUIRED_METRICS[
                component
            ]
        }
        for component in INSURANCE_COMPONENTS
    }


def test_insurance_component_contract_is_complete():
    assert INSURANCE_COMPONENTS == (
        "SOLVENCY_CAPITAL",
        "UNDERWRITING_QUALITY",
        "RESERVE_ADEQUACY",
        "PROFITABILITY",
        "LIQUIDITY_INVESTMENT",
        "GROWTH_QUALITY",
    )

    assert set(
        INSURANCE_COMPONENT_WEIGHTS
    ) == set(INSURANCE_COMPONENTS)

    assert math.isclose(
        sum(
            INSURANCE_COMPONENT_WEIGHTS.values()
        ),
        1.0,
    )


def test_complete_insurance_payload_is_ready():
    payload = _complete_payload()

    result = validate_insurance_model_input(
        payload
    )

    assert result.status == "PASS"
    assert result.ready_for_scoring is True
    assert result.blocker is None

    assert_insurance_model_input_ready(
        payload
    )


def test_missing_component_fails_closed():
    payload = _complete_payload()
    payload.pop("RESERVE_ADEQUACY")

    result = validate_insurance_model_input(
        payload
    )

    assert result.status == "BLOCKED"
    assert result.ready_for_scoring is False
    assert (
        "RESERVE_ADEQUACY"
        in result.missing_components
    )


def test_missing_metric_fails_closed_and_never_zero():
    payload = _complete_payload()
    payload[
        "UNDERWRITING_QUALITY"
    ]["combined_ratio"] = None

    result = validate_insurance_model_input(
        payload
    )

    assert result.status == "BLOCKED"
    assert result.ready_for_scoring is False
    assert (
        "UNDERWRITING_QUALITY.combined_ratio"
        in result.missing_metrics
    )

    with pytest.raises(
        ValueError,
        match="UNDERWRITING_QUALITY.combined_ratio",
    ):
        assert_insurance_model_input_ready(
            payload
        )


def test_unknown_component_weight_is_rejected():
    assert (
        insurance_component_weight(
            "solvency_capital"
        )
        == 0.20
    )

    with pytest.raises(
        KeyError,
        match="UNKNOWN_INSURANCE_COMPONENT",
    ):
        insurance_component_weight(
            "INDUSTRIAL_HEALTH"
        )
