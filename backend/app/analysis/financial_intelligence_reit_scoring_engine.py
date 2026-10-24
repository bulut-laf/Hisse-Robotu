from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Final, Mapping

from app.analysis.financial_intelligence_reit_model_contract import (
    REIT_COMPONENTS,
    REIT_COMPONENT_WEIGHTS,
    REIT_REQUIRED_METRICS,
    assert_reit_model_input_ready,
)

REIT_SCORING_ENGINE_VERSION: Final[str] = "REIT_SCORING_ENGINE_V1"


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
        return _higher_better(
            value,
            bad=low_bad,
            good=low_good,
        )

    return _lower_better(
        value,
        good=high_good,
        bad=high_bad,
    )


METRIC_SCORERS: Final[dict[str, Callable[[float], float]]] = {
    "occupancy_rate":
        lambda v: _higher_better(v, bad=70.0, good=95.0),

    "rental_income_margin":
        lambda v: _higher_better(v, bad=35.0, good=65.0),

    "net_debt_to_assets":
        lambda v: _lower_better(v, good=20.0, bad=60.0),

    "interest_coverage_ratio":
        lambda v: _higher_better(v, bad=1.0, good=4.0),

    "nav_per_share":
        lambda v: _higher_better(v, bad=0.0, good=1.0),

    "price_to_nav_ratio":
        lambda v: _range_best(
            v,
            low_bad=0.30,
            low_good=0.60,
            high_good=0.95,
            high_bad=1.30,
        ),

    "roe":
        lambda v: _higher_better(v, bad=3.0, good=18.0),

    "roa":
        lambda v: _higher_better(v, bad=1.0, good=8.0),

    "ffo_margin":
        lambda v: _higher_better(v, bad=15.0, good=45.0),

    "ffo_payout_ratio":
        lambda v: _range_best(
            v,
            low_bad=10.0,
            low_good=30.0,
            high_good=80.0,
            high_bad=110.0,
        ),

    "operating_cash_flow_to_dividend":
        lambda v: _higher_better(v, bad=0.7, good=1.5),

    "rental_income_growth":
        lambda v: _range_best(
            v,
            low_bad=-10.0,
            low_good=0.0,
            high_good=30.0,
            high_bad=60.0,
        ),

    "ffo_growth":
        lambda v: _higher_better(v, bad=-15.0, good=25.0),

    "nav_growth":
        lambda v: _higher_better(v, bad=-10.0, good=20.0),
}


@dataclass(frozen=True)
class ReitScoreResult:
    status: str
    total_score: float | None
    component_scores: Mapping[str, float]
    metric_scores: Mapping[str, float]
    blocker: str | None
    model_version: str


def _number(value: Any, metric: str) -> float:
    if isinstance(value, bool):
        raise ValueError(
            f"REIT_METRIC_NOT_NUMERIC:{metric}"
        )

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"REIT_METRIC_NOT_NUMERIC:{metric}"
        ) from exc


def score_reit_model(
    payload: Mapping[str, Any],
) -> ReitScoreResult:
    try:
        assert_reit_model_input_ready(payload)
    except ValueError as exc:
        return ReitScoreResult(
            status="BLOCKED",
            total_score=None,
            component_scores={},
            metric_scores={},
            blocker=str(exc),
            model_version=REIT_SCORING_ENGINE_VERSION,
        )

    metric_scores: dict[str, float] = {}
    component_scores: dict[str, float] = {}

    for component in REIT_COMPONENTS:
        block = payload[component]
        scores: list[float] = []

        for metric in REIT_REQUIRED_METRICS[component]:
            scorer = METRIC_SCORERS.get(metric)

            if scorer is None:
                return ReitScoreResult(
                    status="BLOCKED",
                    total_score=None,
                    component_scores={},
                    metric_scores={},
                    blocker=f"REIT_METRIC_SCORER_MISSING:{metric}",
                    model_version=REIT_SCORING_ENGINE_VERSION,
                )

            value = _number(
                block[metric],
                f"{component}.{metric}",
            )

            score = _clamp(
                scorer(value)
            )

            metric_scores[
                f"{component}.{metric}"
            ] = score

            scores.append(score)

        component_scores[component] = (
            sum(scores) / len(scores)
        )

    total = sum(
        component_scores[component]
        * REIT_COMPONENT_WEIGHTS[component]
        for component in REIT_COMPONENTS
    )

    return ReitScoreResult(
        status="PASS",
        total_score=_clamp(total),
        component_scores=component_scores,
        metric_scores=metric_scores,
        blocker=None,
        model_version=REIT_SCORING_ENGINE_VERSION,
    )


__all__ = [
    "REIT_SCORING_ENGINE_VERSION",
    "ReitScoreResult",
    "score_reit_model",
]
