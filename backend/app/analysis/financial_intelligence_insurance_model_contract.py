from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Mapping


INSURANCE_MODEL_VERSION: Final[str] = "INSURANCE_MODEL_CONTRACT_V1"

INSURANCE_COMPONENTS: Final[tuple[str, ...]] = (
    "SOLVENCY_CAPITAL",
    "UNDERWRITING_QUALITY",
    "RESERVE_ADEQUACY",
    "PROFITABILITY",
    "LIQUIDITY_INVESTMENT",
    "GROWTH_QUALITY",
)

INSURANCE_COMPONENT_WEIGHTS: Final[dict[str, float]] = {
    "SOLVENCY_CAPITAL": 0.20,
    "UNDERWRITING_QUALITY": 0.20,
    "RESERVE_ADEQUACY": 0.20,
    "PROFITABILITY": 0.15,
    "LIQUIDITY_INVESTMENT": 0.15,
    "GROWTH_QUALITY": 0.10,
}

INSURANCE_REQUIRED_METRICS: Final[dict[str, tuple[str, ...]]] = {
    "SOLVENCY_CAPITAL": (
        "solvency_ratio",
        "equity_to_assets_ratio",
    ),
    "UNDERWRITING_QUALITY": (
        "loss_ratio",
        "expense_ratio",
        "combined_ratio",
    ),
    "RESERVE_ADEQUACY": (
        "technical_reserve_coverage",
        "claims_reserve_growth",
    ),
    "PROFITABILITY": (
        "roe",
        "roa",
        "underwriting_margin",
    ),
    "LIQUIDITY_INVESTMENT": (
        "liquidity_ratio",
        "investment_yield",
    ),
    "GROWTH_QUALITY": (
        "premium_growth",
        "net_income_growth",
    ),
}


@dataclass(frozen=True)
class InsuranceModelValidation:
    status: str
    missing_components: tuple[str, ...]
    missing_metrics: tuple[str, ...]
    ready_for_scoring: bool
    blocker: str | None


def validate_insurance_model_input(
    payload: Mapping[str, Any],
) -> InsuranceModelValidation:
    missing_components: list[str] = []
    missing_metrics: list[str] = []

    for component in INSURANCE_COMPONENTS:
        block = payload.get(component)

        if not isinstance(block, Mapping):
            missing_components.append(component)
            continue

        for metric in INSURANCE_REQUIRED_METRICS[component]:
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

        return InsuranceModelValidation(
            status="BLOCKED",
            missing_components=tuple(missing_components),
            missing_metrics=tuple(missing_metrics),
            ready_for_scoring=False,
            blocker=";".join(parts),
        )

    return InsuranceModelValidation(
        status="PASS",
        missing_components=(),
        missing_metrics=(),
        ready_for_scoring=True,
        blocker=None,
    )


def assert_insurance_model_input_ready(
    payload: Mapping[str, Any],
) -> None:
    result = validate_insurance_model_input(payload)

    if not result.ready_for_scoring:
        raise ValueError(
            result.blocker
            or "INSURANCE_MODEL_INPUT_NOT_READY"
        )


def insurance_component_weight(component: str) -> float:
    key = str(component).strip().upper()

    if key not in INSURANCE_COMPONENT_WEIGHTS:
        raise KeyError(
            f"UNKNOWN_INSURANCE_COMPONENT:{key}"
        )

    return INSURANCE_COMPONENT_WEIGHTS[key]


__all__ = [
    "INSURANCE_MODEL_VERSION",
    "INSURANCE_COMPONENTS",
    "INSURANCE_COMPONENT_WEIGHTS",
    "INSURANCE_REQUIRED_METRICS",
    "InsuranceModelValidation",
    "validate_insurance_model_input",
    "assert_insurance_model_input_ready",
    "insurance_component_weight",
]
