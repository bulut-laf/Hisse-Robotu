from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.app.analysis.ranking_memory import RankObservation


HORIZONS: tuple[int, ...] = (1, 3, 5, 10)


@dataclass(frozen=True)
class EarlyVisibilityOutcome:
    symbol: str
    entry_as_of: str
    entry_rank: int
    entry_universe_size: int
    horizon_sessions: int
    outcome_as_of: str | None
    outcome_rank: int | None
    outcome_universe_size: int | None
    rank_gain: int | None
    normalized_gain: float | None
    reached_top100: bool | None
    reached_top50: bool | None
    reached_top30: bool | None
    retained_gain: bool | None
    available: bool


@dataclass(frozen=True)
class EarlyVisibilityValidationSummary:
    total_entries: int
    evaluated_outcomes: int
    horizon_sessions: int
    top100_conversion_rate: float | None
    top50_conversion_rate: float | None
    top30_conversion_rate: float | None
    positive_rank_gain_rate: float | None
    retention_rate: float | None
    unavailable_rate: float


def _normalized_position(rank: int, universe_size: int) -> float:
    if universe_size <= 0:
        raise ValueError("universe_size must be positive")
    return rank / universe_size


def _symbol_history(
    observations: Iterable[RankObservation],
    symbol: str,
) -> tuple[RankObservation, ...]:
    target = str(symbol).removesuffix(".IS").upper().strip()
    return tuple(
        sorted(
            (item for item in observations if item.symbol == target),
            key=lambda item: item.as_of,
        )
    )


def evaluate_entry_outcomes(
    observations: Iterable[RankObservation],
    *,
    symbol: str,
    entry_as_of: str,
) -> tuple[EarlyVisibilityOutcome, ...]:
    history = _symbol_history(observations, symbol)
    entry_index = next(
        (i for i, item in enumerate(history) if item.as_of == entry_as_of),
        None,
    )
    if entry_index is None:
        return ()

    entry = history[entry_index]
    outcomes: list[EarlyVisibilityOutcome] = []

    for horizon in HORIZONS:
        target_index = entry_index + horizon
        if target_index >= len(history):
            outcomes.append(
                EarlyVisibilityOutcome(
                    symbol=entry.symbol,
                    entry_as_of=entry.as_of,
                    entry_rank=entry.rank,
                    entry_universe_size=entry.ranked_universe_size,
                    horizon_sessions=horizon,
                    outcome_as_of=None,
                    outcome_rank=None,
                    outcome_universe_size=None,
                    rank_gain=None,
                    normalized_gain=None,
                    reached_top100=None,
                    reached_top50=None,
                    reached_top30=None,
                    retained_gain=None,
                    available=False,
                )
            )
            continue

        outcome = history[target_index]
        comparable = (
            entry.universe_source == outcome.universe_source
            and entry.profile_name == outcome.profile_name
            and entry.ranked_universe_size > 0
            and outcome.ranked_universe_size > 0
        )

        rank_gain = entry.rank - outcome.rank if comparable else None
        normalized_gain = (
            _normalized_position(entry.rank, entry.ranked_universe_size)
            - _normalized_position(outcome.rank, outcome.ranked_universe_size)
            if comparable
            else None
        )

        outcomes.append(
            EarlyVisibilityOutcome(
                symbol=entry.symbol,
                entry_as_of=entry.as_of,
                entry_rank=entry.rank,
                entry_universe_size=entry.ranked_universe_size,
                horizon_sessions=horizon,
                outcome_as_of=outcome.as_of,
                outcome_rank=outcome.rank,
                outcome_universe_size=outcome.ranked_universe_size,
                rank_gain=rank_gain,
                normalized_gain=normalized_gain,
                reached_top100=(outcome.rank <= 100) if comparable else None,
                reached_top50=(outcome.rank <= 50) if comparable else None,
                reached_top30=(outcome.rank <= 30) if comparable else None,
                retained_gain=(outcome.rank < entry.rank) if comparable else None,
                available=comparable,
            )
        )

    return tuple(outcomes)


def summarize_outcomes(
    outcomes: Iterable[EarlyVisibilityOutcome],
    *,
    horizon_sessions: int,
) -> EarlyVisibilityValidationSummary:
    selected = tuple(
        item for item in outcomes if item.horizon_sessions == horizon_sessions
    )
    if not selected:
        return EarlyVisibilityValidationSummary(
            total_entries=0,
            evaluated_outcomes=0,
            horizon_sessions=horizon_sessions,
            top100_conversion_rate=None,
            top50_conversion_rate=None,
            top30_conversion_rate=None,
            positive_rank_gain_rate=None,
            retention_rate=None,
            unavailable_rate=0.0,
        )

    available = tuple(item for item in selected if item.available)
    evaluated = len(available)
    total = len(selected)

    def rate(predicate):
        if evaluated == 0:
            return None
        return sum(1 for item in available if predicate(item)) / evaluated

    return EarlyVisibilityValidationSummary(
        total_entries=total,
        evaluated_outcomes=evaluated,
        horizon_sessions=horizon_sessions,
        top100_conversion_rate=rate(lambda item: item.reached_top100 is True),
        top50_conversion_rate=rate(lambda item: item.reached_top50 is True),
        top30_conversion_rate=rate(lambda item: item.reached_top30 is True),
        positive_rank_gain_rate=rate(
            lambda item: item.rank_gain is not None and item.rank_gain > 0
        ),
        retention_rate=rate(lambda item: item.retained_gain is True),
        unavailable_rate=(total - evaluated) / total,
    )


def build_validation_outcomes(
    observations: Iterable[RankObservation],
    entries: Iterable[tuple[str, str]],
) -> tuple[EarlyVisibilityOutcome, ...]:
    items = tuple(observations)
    result: list[EarlyVisibilityOutcome] = []
    for symbol, entry_as_of in entries:
        result.extend(
            evaluate_entry_outcomes(
                items,
                symbol=symbol,
                entry_as_of=entry_as_of,
            )
        )
    return tuple(result)
