from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EarlyVisibilityTrackingContext:
    symbol: str
    visibility_state: str
    research_priority: str
    source: str = "EARLY_VISIBILITY"


def build_early_visibility_tracking_context(
    *,
    symbol: str,
    visibility_state: str,
    research_priority: str,
) -> EarlyVisibilityTrackingContext:
    return EarlyVisibilityTrackingContext(
        symbol=str(symbol).upper().strip(),
        visibility_state=visibility_state,
        research_priority=research_priority,
    )