from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Mapping


BANK_MODEL_VERSION: Final[str] = "BANK_MODEL_CONTRACT_V1"

BANK_COMPONENTS: Final[tuple[str, ...]] = (
    "CAPITAL_ADEQUACY",
    "ASSET_QUALITY",
    "PROFITABILITY",
    "FUNDING_LIQUIDITY",
    "EFFICIENCY",
    "GROWTH_QUALITY",
)

BANK_COMPONENT_WEIGHTS: Final[dict[str, float]] = {
    "CAPITAL_ADEQUACY": 0.20,
    "ASSET_QUALITY": 0.20,
    "PROFITABILITY": 0.20,
    "FUNDING_LIQUIDITY": 0.15,
    "EFFICIENCY": 0.15,
    "GROWTH_QUALITY": 0.10,
}

BANK_REQUIRED_METRICS: Final[dict[str, tuple[str, ...]]] = {
    "CAPITAL_ADEQUACY": (
        "capital_adequacy_ratio",
        "tier1_capital_ratio",
    ),
    "ASSET_QUALITY": (
        "npl_ratio",
        "npl_coverage_ratio",
    ),
    "PROFITABILITY": (
        "roe",
        "roa",
        "net_interest_margin",
    ),
    "FUNDING_LIQUIDITY": (
        "loan_to_deposit_ratio",
        "liquidity_ratio",
    ),
    "EFFICIENCY": (
        "cost_to_income_ratio",
    ),
    "GROWTH_QUALITY": (
        "loan_growth",
        "deposit_growth",
        "net_income_growth",
    ),
}


@dataclass(frozen=True)
class BankModelValidation:
    status: str
    missing_components: tuple[str, ...]
    missing_metrics: tuple[str, ...]
    ready_for_scoring: bool
    blocker: str | None


def validate_bank_model_input(
    payload: Mapping[str, Any],
) -> BankModelValidation:
    missing_components: list[str] = []
    missing_metrics: list[str] = []

    for component in BANK_COMPONENTS:
        block = payload.get(component)

        if not isinstance(block, Mapping):
            missing_components.append(component)
            continue

        for metric in BANK_REQUIRED_METRICS[component]:
            if metric not in block or block.get(metric) is None:
                missing_metrics.append(f"{component}.{metric}")

    if missing_components or missing_metrics:
        parts: list[str] = []
        if missing_components:
            parts.append(
                "MISSING_COMPONENTS:" + ",".join(missing_components)
            )
        if missing_metrics:
            parts.append(
                "MISSING_METRICS:" + ",".join(missing_metrics)
            )

        return BankModelValidation(
            status="BLOCKED",
            missing_components=tuple(missing_components),
            missing_metrics=tuple(missing_metrics),
            ready_for_scoring=False,
            blocker=";".join(parts),
        )

    return BankModelValidation(
        status="PASS",
        missing_components=(),
        missing_metrics=(),
        ready_for_scoring=True,
        blocker=None,
    )


def assert_bank_model_input_ready(
    payload: Mapping[str, Any],
) -> None:
    result = validate_bank_model_input(payload)
    if not result.ready_for_scoring:
        raise ValueError(
            result.blocker or "BANK_MODEL_INPUT_NOT_READY"
        )


def bank_component_weight(component: str) -> float:
    key = str(component).strip().upper()

    if key not in BANK_COMPONENT_WEIGHTS:
        raise KeyError(f"UNKNOWN_BANK_COMPONENT:{key}")

    return BANK_COMPONENT_WEIGHTS[key]


__all__ = [
    "BANK_MODEL_VERSION",
    "BANK_COMPONENTS",
    "BANK_COMPONENT_WEIGHTS",
    "BANK_REQUIRED_METRICS",
    "BankModelValidation",
    "validate_bank_model_input",
    "assert_bank_model_input_ready",
    "bank_component_weight",
]
