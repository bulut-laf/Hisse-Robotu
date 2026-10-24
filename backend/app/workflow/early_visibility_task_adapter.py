from __future__ import annotations

from dataclasses import dataclass

from backend.app.analysis.early_visibility_tracking_bridge import (
    EarlyVisibilityTrackingContext,
)


@dataclass(frozen=True)
class EarlyVisibilityTaskHint:
    symbol: str
    title: str
    target_module: str
    research_priority: str


def build_early_visibility_task_hint(
    context: EarlyVisibilityTrackingContext,
) -> EarlyVisibilityTaskHint:
    return EarlyVisibilityTaskHint(
        symbol=context.symbol,
        title="Erken Görünürlük incelemesi",
        target_module="Erken Görünürlük",
        research_priority=context.research_priority,
    )
