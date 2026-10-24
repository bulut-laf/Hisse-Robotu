from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EarlyVisibilityTaskCompletion:
    symbol: str
    state: str
    completed: bool
    task_type: str
    source: str = "EARLY_VISIBILITY"


def complete_early_visibility_task(symbol: str):
    return EarlyVisibilityTaskCompletion(
        symbol=str(symbol).upper(),
        state="COMPLETED",
        completed=True,
        task_type="RESEARCH_REVIEW",
    )
