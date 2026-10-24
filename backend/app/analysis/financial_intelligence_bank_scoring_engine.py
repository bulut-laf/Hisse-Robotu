from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Final, Mapping

from app.analysis.financial_intelligence_bank_model_contract import (
    BANK_COMPONENTS,
    BANK_COMPONENT_WEIGHTS,
    BANK_REQUIRED_METRICS,
    assert_bank_model_input_ready,
)


BANK_SCORING_ENGINE_VERSION: Final[str] = "BANK_SCORING_ENGINE_V1"


def _clamp(score: float) -> float:
    return max(0.0, min(100.0, float(score)))


def _higher_better(
    value: float,
    *,
    bad: float,
    good: float,
) -> float:
    if good <= bad:
        raise ValueError("INVALID_HIGHER_BETTER_RANGE")

    if value <= bad:
        return 0.0
    if value >= good:
        return 100.0

    return _clamp(
        (value - bad) / (good - bad) * 100.0
    )


def _lower_better(
    value: float,
    *,
    good: float,
    bad: float,
) -> float:
    if bad <= good:
        raise ValueError("INVALID_LOWER_BETTER_RANGE")

    if value <= good:
        return 100.0
    if value >= bad:
        return 0.0

    return _clamp(
        (bad - value) / (bad - good) * 100.0
    )


def _range_best(
    value: float,
    *,
    low_bad: float,
    low_good: float,
    high_good: float,
    high_bad: float,
) -> float:
    if not (
        low_bad < low_good <= high_good < high_bad
    ):
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


def _growth_quality_score(
    loan_growth: float,
    deposit_growth: float,
    net_income_growth: float,
) -> float:
    loan_deposit_gap = abs(
        loan_growth - deposit_growth
    )

    balance_score = _lower_better(
        loan_deposit_gap,
        good=5.0,
        bad=25.0,
    )

    income_score = _higher_better(
        net_income_growth,
        bad=-10.0,
        good=25.0,
    )

    loan_growth_score = _range_best(
        loan_growth,
        low_bad=-10.0,
        low_good=0.0,
        high_good=25.0,
        high_bad=50.0,
    )

    return _clamp(
        balance_score * 0.35
        + income_score * 0.40
        + loan_growth_score * 0.25
    )


METRIC_SCORERS: Final[
    dict[str, Callable[[float], float]]
] = {
    "capital_adequacy_ratio":
        lambda v: _higher_better(v, bad=10.0, good=18.0),

    "tier1_capital_ratio":
        lambda v: _higher_better(v, bad=8.0, good=15.0),

    "npl_ratio":
        lambda v: _lower_better(v, good=2.0, bad=8.0),

    "npl_coverage_ratio":
        lambda v: _higher_better(v, bad=50.0, good=100.0),

    "roe":
        lambda v: _higher_better(v, bad=5.0, good=25.0),

    "roa":
        lambda v: _higher_better(v, bad=0.5, good=3.0),

    "net_interest_margin":
        lambda v: _higher_better(v, bad=1.5, good=6.0),

    "loan_to_deposit_ratio":
        lambda v: _range_best(
            v,
            low_bad=50.0,
            low_good=70.0,
            high_good=110.0,
            high_bad=140.0,
        ),

    "liquidity_ratio":
        lambda v: _higher_better(v, bad=80.0, good=130.0),

    "cost_to_income_ratio":
        lambda v: _lower_better(v, good=35.0, bad=70.0),
}


@dataclass(frozen=True)
class BankScoreResult:
    status: str
    total_score: float | None
    component_scores: Mapping[str, float]
    metric_scores: Mapping[str, float]
    blocker: str | None
    model_version: str


def _number(value: Any, metric: str) -> float:
    if isinstance(value, bool):
        raise ValueError(
            f"BANK_METRIC_NOT_NUMERIC:{metric}"
        )

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"BANK_METRIC_NOT_NUMERIC:{metric}"
        ) from exc


def score_bank_model(
    payload: Mapping[str, Any],
) -> BankScoreResult:
    try:
        assert_bank_model_input_ready(payload)
    except ValueError as exc:
        return BankScoreResult(
            status="BLOCKED",
            total_score=None,
            component_scores={},
            metric_scores={},
            blocker=str(exc),
            model_version=BANK_SCORING_ENGINE_VERSION,
        )

    metric_scores: dict[str, float] = {}
    component_scores: dict[str, float] = {}

    for component in BANK_COMPONENTS:
        block = payload[component]

        if component == "GROWTH_QUALITY":
            loan_growth = _number(
                block["loan_growth"],
                "GROWTH_QUALITY.loan_growth",
            )
            deposit_growth = _number(
                block["deposit_growth"],
                "GROWTH_QUALITY.deposit_growth",
            )
            net_income_growth = _number(
                block["net_income_growth"],
                "GROWTH_QUALITY.net_income_growth",
            )

            growth_score = _growth_quality_score(
                loan_growth,
                deposit_growth,
                net_income_growth,
            )

            metric_scores[
                "GROWTH_QUALITY.composite"
            ] = growth_score

            component_scores[component] = growth_score
            continue

        component_metric_scores: list[float] = []

        for metric in BANK_REQUIRED_METRICS[component]:
            scorer = METRIC_SCORERS.get(metric)

            if scorer is None:
                return BankScoreResult(
                    status="BLOCKED",
                    total_score=None,
                    component_scores={},
                    metric_scores={},
                    blocker=f"BANK_METRIC_SCORER_MISSING:{metric}",
                    model_version=BANK_SCORING_ENGINE_VERSION,
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
        * BANK_COMPONENT_WEIGHTS[component]
        for component in BANK_COMPONENTS
    )

    return BankScoreResult(
        status="PASS",
        total_score=_clamp(total),
        component_scores=component_scores,
        metric_scores=metric_scores,
        blocker=None,
        model_version=BANK_SCORING_ENGINE_VERSION,
    )


__all__ = [
    "BANK_SCORING_ENGINE_VERSION",
    "BankScoreResult",
    "score_bank_model",
]
