from __future__ import annotations

from dataclasses import dataclass

from backend.app.workflow.early_visibility_surface_adapter import (
    EarlyVisibilitySurfaceItem,
)


@dataclass(frozen=True)
class EarlyVisibilityFeedbackRecord:
    symbol: str
    observed_action: str
    priority: str
    source: str = "EARLY_VISIBILITY"


def build_early_visibility_feedback_record(
    item: EarlyVisibilitySurfaceItem,
) -> EarlyVisibilityFeedbackRecord:
    return EarlyVisibilityFeedbackRecord(
        symbol=item.symbol,
        observed_action=item.label,
        priority=item.priority,
    )
