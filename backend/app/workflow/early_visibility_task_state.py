from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EarlyVisibilityTaskState:
    symbol: str
    state: str
    task_type: str
    source: str = "EARLY_VISIBILITY"


def build_early_visibility_task_state(symbol: str, state: str = "CREATED"):
    return EarlyVisibilityTaskState(
        symbol=str(symbol).upper(),
        state=str(state).upper(),
        task_type="RESEARCH_REVIEW",
    )
