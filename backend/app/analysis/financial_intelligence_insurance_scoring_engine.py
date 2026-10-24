from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Final, Mapping

from app.analysis.financial_intelligence_insurance_model_contract import (
    INSURANCE_COMPONENTS,
    INSURANCE_COMPONENT_WEIGHTS,
    INSURANCE_REQUIRED_METRICS,
    assert_insurance_model_input_ready,
)

INSURANCE_SCORING_ENGINE_VERSION: Final[str] = "INSURANCE_SCORING_ENGINE_V1"


def _clamp(score: float) -> float:
    return max(0.0, min(100.0, float(score)))


def _higher_better(value: float, *, bad: float, good: float) -> float:
    if good <= bad:
        raise ValueError("INVALID_HIGHER_BETTER_RANGE")
    if value <= bad:
        return 0.0
    if value >= good:
        return 100.0
    return _clamp((value - bad) / (good - bad) * 100.0)


def _lower_better(value: float, *, good: float, bad: float) -> float:
    if bad <= good:
        raise ValueError("INVALID_LOWER_BETTER_RANGE")
    if value <= good:
        return 100.0
    if value >= bad:
        return 0.0
    return _clamp((bad - value) / (bad - good) * 100.0)


def _range_best(
    value: float,
    *,
    low_bad: float,
    low_good: float,
    high_good: float,
    high_bad: float,
) -> float:
    if not (low_bad < low_good <= high_good < high_bad):
        raise ValueError("INVALID_RANGE_BEST_THRESHOLDS")
    if low_good <= value <= high_good:
        return 100.0
    if value <= low_bad or value >= high_bad:
        return 0.0
    if value < low_good:
        return _higher_better(value, bad=low_bad, good=low_good)
    return _lower_better(value, good=high_good, bad=high_bad)


METRIC_SCORERS: Final[dict[str, Callable[[float], float]]] = {
    "solvency_ratio":
        lambda v: _higher_better(v, bad=100.0, good=180.0),

    "equity_to_assets_ratio":
        lambda v: _higher_better(v, bad=8.0, good=20.0),

    "loss_ratio":
        lambda v: _lower_better(v, good=55.0, bad=85.0),

    "expense_ratio":
        lambda v: _lower_better(v, good=25.0, bad=45.0),

    "combined_ratio":
        lambda v: _lower_better(v, good=90.0, bad=110.0),

    "technical_reserve_coverage":
        lambda v: _higher_better(v, bad=100.0, good=140.0),

    "claims_reserve_growth":
        lambda v: _range_best(
            v,
            low_bad=-15.0,
            low_good=0.0,
            high_good=25.0,
            high_bad=50.0,
        ),

    "roe":
        lambda v: _higher_better(v, bad=5.0, good=25.0),

    "roa":
        lambda v: _higher_better(v, bad=0.5, good=3.0),

    "underwriting_margin":
        lambda v: _higher_better(v, bad=-5.0, good=15.0),

    "liquidity_ratio":
        lambda v: _higher_better(v, bad=80.0, good=130.0),

    "investment_yield":
        lambda v: _higher_better(v, bad=0.0, good=15.0),

    "premium_growth":
        lambda v: _range_best(
            v,
            low_bad=-10.0,
            low_good=0.0,
            high_good=30.0,
            high_bad=60.0,
        ),

    "net_income_growth":
        lambda v: _higher_better(v, bad=-20.0, good=30.0),
}


@dataclass(frozen=True)
class InsuranceScoreResult:
    status: str
    total_score: float | None
    component_scores: Mapping[str, float]
    metric_scores: Mapping[str, float]
    blocker: str | None
    model_version: str


def _number(value: Any, metric: str) -> float:
    if isinstance(value, bool):
        raise ValueError(
            f"INSURANCE_METRIC_NOT_NUMERIC:{metric}"
        )
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"INSURANCE_METRIC_NOT_NUMERIC:{metric}"
        ) from exc


def score_insurance_model(
    payload: Mapping[str, Any],
) -> InsuranceScoreResult:
    try:
        assert_insurance_model_input_ready(payload)
    except ValueError as exc:
        return InsuranceScoreResult(
            status="BLOCKED",
            total_score=None,
            component_scores={},
            metric_scores={},
            blocker=str(exc),
            model_version=INSURANCE_SCORING_ENGINE_VERSION,
        )

    metric_scores: dict[str, float] = {}
    component_scores: dict[str, float] = {}

    for component in INSURANCE_COMPONENTS:
        block = payload[component]
        component_metric_scores: list[float] = []

        for metric in INSURANCE_REQUIRED_METRICS[component]:
            scorer = METRIC_SCORERS.get(metric)

            if scorer is None:
                return InsuranceScoreResult(
                    status="BLOCKED",
                    total_score=None,
                    component_scores={},
                    metric_scores={},
                    blocker=f"INSURANCE_METRIC_SCORER_MISSING:{metric}",
                    model_version=INSURANCE_SCORING_ENGINE_VERSION,
                )

            value = _number(
                block[metric],
                f"{component}.{metric}",
            )

            score = _clamp(scorer(value))

            metric_scores[
                f"{component}.{metric}"
            ] = score

            component_metric_scores.append(score)

        component_scores[component] = (
            sum(component_metric_scores)
            / len(component_metric_scores)
        )

    total = sum(
        component_scores[component]
        * INSURANCE_COMPONENT_WEIGHTS[component]
        for component in INSURANCE_COMPONENTS
    )

    return InsuranceScoreResult(
        status="PASS",
        total_score=_clamp(total),
        component_scores=component_scores,
        metric_scores=metric_scores,
        blocker=None,
        model_version=INSURANCE_SCORING_ENGINE_VERSION,
    )


__all__ = [
    "INSURANCE_SCORING_ENGINE_VERSION",
    "InsuranceScoreResult",
    "score_insurance_model",
]
