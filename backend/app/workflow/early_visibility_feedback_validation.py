from __future__ import annotations

from dataclasses import dataclass

from backend.app.workflow.early_visibility_feedback_loop import (
    EarlyVisibilityFeedbackRecord,
)


@dataclass(frozen=True)
class EarlyVisibilityFeedbackValidation:
    symbol: str
    valid: bool
    source: str


def validate_early_visibility_feedback(
    record: EarlyVisibilityFeedbackRecord,
) -> EarlyVisibilityFeedbackValidation:
    return EarlyVisibilityFeedbackValidation(
        symbol=record.symbol,
        valid=bool(record.symbol and record.priority),
        source=record.source,
    )
