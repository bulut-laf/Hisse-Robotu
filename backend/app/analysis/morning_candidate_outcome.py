from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class MorningCandidateOutcome:
    symbol: str
    morning_rank: int
    observation_state: str
    close_price: float | None
    change_percent: float | None
    outcome_state: str


def build_morning_candidate_outcomes(
    candidates: Iterable[object],
    close_context: dict[str, object] | None = None,
) -> tuple[MorningCandidateOutcome, ...]:
    close_context = close_context or {}

    outcomes = []

    for candidate in candidates:
        symbol = str(getattr(candidate, "symbol", "")).upper()
        close_data = close_context.get(symbol)

        change = None
        price = None

        if close_data is not None:
            price = getattr(close_data, "close_price", None)
            change = getattr(close_data, "change_percent", None)

        outcomes.append(
            MorningCandidateOutcome(
                symbol=symbol,
                morning_rank=int(getattr(candidate, "rank", 0)),
                observation_state="RECORDED",
                close_price=price,
                change_percent=change,
                outcome_state=(
                    "CLOSE_DATA_AVAILABLE"
                    if close_data is not None
                    else "WAITING_FOR_CLOSE_DATA"
                ),
            )
        )

    return tuple(outcomes)
