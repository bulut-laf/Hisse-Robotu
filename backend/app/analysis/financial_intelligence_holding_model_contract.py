from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Mapping


HOLDING_MODEL_VERSION: Final[str] = "HOLDING_MODEL_CONTRACT_V1"

HOLDING_COMPONENTS: Final[tuple[str, ...]] = (
    "NAV_QUALITY",
    "SUBSIDIARY_QUALITY",
    "HOLDING_LEVERAGE",
    "CASH_FLOW_QUALITY",
    "PROFITABILITY",
    "GROWTH_QUALITY",
)

HOLDING_COMPONENT_WEIGHTS: Final[dict[str, float]] = {
    "NAV_QUALITY": 0.25,
    "SUBSIDIARY_QUALITY": 0.20,
    "HOLDING_LEVERAGE": 0.20,
    "CASH_FLOW_QUALITY": 0.15,
    "PROFITABILITY": 0.10,
    "GROWTH_QUALITY": 0.10,
}

HOLDING_REQUIRED_METRICS: Final[dict[str, tuple[str, ...]]] = {
    "NAV_QUALITY": (
        "nav_per_share",
        "price_to_nav_ratio",
    ),
    "SUBSIDIARY_QUALITY": (
        "listed_subsidiary_value_share",
        "subsidiary_dividend_coverage",
    ),
    "HOLDING_LEVERAGE": (
        "net_debt_to_nav",
        "interest_coverage_ratio",
    ),
    "CASH_FLOW_QUALITY": (
        "holding_operating_cash_flow",
        "dividend_income_to_financing_cost",
    ),
    "PROFITABILITY": (
        "roe",
        "roa",
    ),
    "GROWTH_QUALITY": (
        "nav_growth",
        "net_income_growth",
        "dividend_income_growth",
    ),
}


@dataclass(frozen=True)
class HoldingModelValidation:
    status: str
    missing_components: tuple[str, ...]
    missing_metrics: tuple[str, ...]
    ready_for_scoring: bool
    blocker: str | None


def validate_holding_model_input(
    payload: Mapping[str, Any],
) -> HoldingModelValidation:
    missing_components: list[str] = []
    missing_metrics: list[str] = []

    for component in HOLDING_COMPONENTS:
        block = payload.get(component)

        if not isinstance(block, Mapping):
            missing_components.append(component)
            continue

        for metric in HOLDING_REQUIRED_METRICS[component]:
            if metric not in block or block.get(metric) is None:
                missing_metrics.append(f"{component}.{metric}")

    if missing_components or missing_metrics:
        parts: list[str] = []

        if missing_components:
            parts.append(
                "MISSING_COMPONENTS:"
                + ",".join(missing_components)
            )

        if missing_metrics:
            parts.append(
                "MISSING_METRICS:"
                + ",".join(missing_metrics)
            )

        return HoldingModelValidation(
            status="BLOCKED",
            missing_components=tuple(missing_components),
            missing_metrics=tuple(missing_metrics),
            ready_for_scoring=False,
            blocker=";".join(parts),
        )

    return HoldingModelValidation(
        status="PASS",
        missing_components=(),
        missing_metrics=(),
        ready_for_scoring=True,
        blocker=None,
    )


def assert_holding_model_input_ready(
    payload: Mapping[str, Any],
) -> None:
    result = validate_holding_model_input(payload)

    if not result.ready_for_scoring:
        raise ValueError(
            result.blocker
            or "HOLDING_MODEL_INPUT_NOT_READY"
        )


def holding_component_weight(component: str) -> float:
    key = str(component).strip().upper()

    if key not in HOLDING_COMPONENT_WEIGHTS:
        raise KeyError(
            f"UNKNOWN_HOLDING_COMPONENT:{key}"
        )

    return HOLDING_COMPONENT_WEIGHTS[key]


__all__ = [
    "HOLDING_MODEL_VERSION",
    "HOLDING_COMPONENTS",
    "HOLDING_COMPONENT_WEIGHTS",
    "HOLDING_REQUIRED_METRICS",
    "HoldingModelValidation",
    "validate_holding_model_input",
    "assert_holding_model_input_ready",
    "holding_component_weight",
]
