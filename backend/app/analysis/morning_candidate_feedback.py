from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class MorningCandidateFeedback:
    symbol: str
    user_state: str
    note: str
    recorded: bool


def build_morning_candidate_feedback(
    symbol: str,
    user_state: str,
    note: str = "",
) -> MorningCandidateFeedback:
    return MorningCandidateFeedback(
        symbol=str(symbol).upper(),
        user_state=str(user_state).strip(),
        note=str(note).strip(),
        recorded=True,
    )


def summarize_feedback(
    feedback_items: Iterable[MorningCandidateFeedback],
) -> dict[str, int]:
    items = tuple(feedback_items)

    return {
        "total": len(items),
        "reviewed": sum(
            item.user_state.casefold() == "incelendi"
            for item in items
        ),
        "traded": sum(
            item.user_state.casefold() == "işlem yapıldı"
            for item in items
        ),
        "skipped": sum(
            item.user_state.casefold() == "pas geçildi"
            for item in items
        ),
    }
