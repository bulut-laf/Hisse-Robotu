from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Final, Mapping

from app.analysis.financial_intelligence_holding_model_contract import (
    HOLDING_COMPONENTS,
    HOLDING_COMPONENT_WEIGHTS,
    HOLDING_REQUIRED_METRICS,
    assert_holding_model_input_ready,
)

HOLDING_SCORING_ENGINE_VERSION: Final[str] = "HOLDING_SCORING_ENGINE_V1"


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
    "nav_per_share":
        lambda v: _higher_better(v, bad=0.0, good=1.0),

    "price_to_nav_ratio":
        lambda v: _range_best(
            v,
            low_bad=0.25,
            low_good=0.50,
            high_good=0.90,
            high_bad=1.20,
        ),

    "listed_subsidiary_value_share":
        lambda v: _higher_better(v, bad=20.0, good=70.0),

    "subsidiary_dividend_coverage":
        lambda v: _higher_better(v, bad=0.5, good=1.5),

    "net_debt_to_nav":
        lambda v: _lower_better(v, good=10.0, bad=50.0),

    "interest_coverage_ratio":
        lambda v: _higher_better(v, bad=1.0, good=4.0),

    "holding_operating_cash_flow":
        lambda v: _higher_better(v, bad=0.0, good=1.0),

    "dividend_income_to_financing_cost":
        lambda v: _higher_better(v, bad=0.5, good=2.0),

    "roe":
        lambda v: _higher_better(v, bad=5.0, good=20.0),

    "roa":
        lambda v: _higher_better(v, bad=1.0, good=8.0),

    "nav_growth":
        lambda v: _higher_better(v, bad=-10.0, good=20.0),

    "net_income_growth":
        lambda v: _higher_better(v, bad=-20.0, good=30.0),

    "dividend_income_growth":
        lambda v: _higher_better(v, bad=-15.0, good=25.0),
}


@dataclass(frozen=True)
class HoldingScoreResult:
    status: str
    total_score: float | None
    component_scores: Mapping[str, float]
    metric_scores: Mapping[str, float]
    blocker: str | None
    model_version: str


def _number(value: Any, metric: str) -> float:
    if isinstance(value, bool):
        raise ValueError(
            f"HOLDING_METRIC_NOT_NUMERIC:{metric}"
        )

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"HOLDING_METRIC_NOT_NUMERIC:{metric}"
        ) from exc


def score_holding_model(
    payload: Mapping[str, Any],
) -> HoldingScoreResult:
    try:
        assert_holding_model_input_ready(payload)
    except ValueError as exc:
        return HoldingScoreResult(
            status="BLOCKED",
            total_score=None,
            component_scores={},
            metric_scores={},
            blocker=str(exc),
            model_version=HOLDING_SCORING_ENGINE_VERSION,
        )

    metric_scores: dict[str, float] = {}
    component_scores: dict[str, float] = {}

    for component in HOLDING_COMPONENTS:
        block = payload[component]
        scores: list[float] = []

        for metric in HOLDING_REQUIRED_METRICS[component]:
            scorer = METRIC_SCORERS.get(metric)

            if scorer is None:
                return HoldingScoreResult(
                    status="BLOCKED",
                    total_score=None,
                    component_scores={},
                    metric_scores={},
                    blocker=f"HOLDING_METRIC_SCORER_MISSING:{metric}",
                    model_version=HOLDING_SCORING_ENGINE_VERSION,
                )

            value = _number(
                block[metric],
                f"{component}.{metric}",
            )

            score = _clamp(scorer(value))

            metric_scores[
                f"{component}.{metric}"
            ] = score

            scores.append(score)

        component_scores[component] = (
            sum(scores) / len(scores)
        )

    total = sum(
        component_scores[component]
        * HOLDING_COMPONENT_WEIGHTS[component]
        for component in HOLDING_COMPONENTS
    )

    return HoldingScoreResult(
        status="PASS",
        total_score=_clamp(total),
        component_scores=component_scores,
        metric_scores=metric_scores,
        blocker=None,
        model_version=HOLDING_SCORING_ENGINE_VERSION,
    )


__all__ = [
    "HOLDING_SCORING_ENGINE_VERSION",
    "HoldingScoreResult",
    "score_holding_model",
]
