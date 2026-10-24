from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EarlyVisibilityOperationalContext:
    symbol: str
    task_type: str
    priority: str
    context: str
    source: str = "EARLY_VISIBILITY"


def build_early_visibility_operational_context(
    symbol: str,
    priority: str,
) -> EarlyVisibilityOperationalContext:
    return EarlyVisibilityOperationalContext(
        symbol=str(symbol).upper(),
        task_type="RESEARCH_REVIEW",
        priority=str(priority).upper(),
        context="OPERATIONAL_CONTEXT",
    )
