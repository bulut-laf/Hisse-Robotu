from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Mapping


REIT_MODEL_VERSION: Final[str] = "REIT_MODEL_CONTRACT_V1"

REIT_COMPONENTS: Final[tuple[str, ...]] = (
    "PORTFOLIO_QUALITY",
    "LEVERAGE",
    "NAV_VALUATION",
    "PROFITABILITY",
    "CASH_DISTRIBUTION",
    "GROWTH_QUALITY",
)

REIT_COMPONENT_WEIGHTS: Final[dict[str, float]] = {
    "PORTFOLIO_QUALITY": 0.20,
    "LEVERAGE": 0.20,
    "NAV_VALUATION": 0.20,
    "PROFITABILITY": 0.15,
    "CASH_DISTRIBUTION": 0.15,
    "GROWTH_QUALITY": 0.10,
}

REIT_REQUIRED_METRICS: Final[dict[str, tuple[str, ...]]] = {
    "PORTFOLIO_QUALITY": (
        "occupancy_rate",
        "rental_income_margin",
    ),
    "LEVERAGE": (
        "net_debt_to_assets",
        "interest_coverage_ratio",
    ),
    "NAV_VALUATION": (
        "nav_per_share",
        "price_to_nav_ratio",
    ),
    "PROFITABILITY": (
        "roe",
        "roa",
        "ffo_margin",
    ),
    "CASH_DISTRIBUTION": (
        "ffo_payout_ratio",
        "operating_cash_flow_to_dividend",
    ),
    "GROWTH_QUALITY": (
        "rental_income_growth",
        "ffo_growth",
        "nav_growth",
    ),
}


@dataclass(frozen=True)
class ReitModelValidation:
    status: str
    missing_components: tuple[str, ...]
    missing_metrics: tuple[str, ...]
    ready_for_scoring: bool
    blocker: str | None


def validate_reit_model_input(
    payload: Mapping[str, Any],
) -> ReitModelValidation:
    missing_components: list[str] = []
    missing_metrics: list[str] = []

    for component in REIT_COMPONENTS:
        block = payload.get(component)

        if not isinstance(block, Mapping):
            missing_components.append(component)
            continue

        for metric in REIT_REQUIRED_METRICS[component]:
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

        return ReitModelValidation(
            status="BLOCKED",
            missing_components=tuple(missing_components),
            missing_metrics=tuple(missing_metrics),
            ready_for_scoring=False,
            blocker=";".join(parts),
        )

    return ReitModelValidation(
        status="PASS",
        missing_components=(),
        missing_metrics=(),
        ready_for_scoring=True,
        blocker=None,
    )


def assert_reit_model_input_ready(
    payload: Mapping[str, Any],
) -> None:
    result = validate_reit_model_input(payload)

    if not result.ready_for_scoring:
        raise ValueError(
            result.blocker
            or "REIT_MODEL_INPUT_NOT_READY"
        )


def reit_component_weight(component: str) -> float:
    key = str(component).strip().upper()

    if key not in REIT_COMPONENT_WEIGHTS:
        raise KeyError(
            f"UNKNOWN_REIT_COMPONENT:{key}"
        )

    return REIT_COMPONENT_WEIGHTS[key]


__all__ = [
    "REIT_MODEL_VERSION",
    "REIT_COMPONENTS",
    "REIT_COMPONENT_WEIGHTS",
    "REIT_REQUIRED_METRICS",
    "ReitModelValidation",
    "validate_reit_model_input",
    "assert_reit_model_input_ready",
    "reit_component_weight",
]
