from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EarlyVisibilityTaskLifecycle:
    symbol: str
    state: str
    task_type: str
    source: str = "EARLY_VISIBILITY"


def build_early_visibility_task_lifecycle(symbol: str):
    return EarlyVisibilityTaskLifecycle(
        symbol=str(symbol).upper(),
        state="CREATED",
        task_type="RESEARCH_REVIEW",
    )
