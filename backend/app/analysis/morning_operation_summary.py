from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class MorningOperationSummary:
    candidate_count: int
    recorded_count: int
    available_close_count: int
    pending_close_count: int
    summary_state: str


def build_morning_operation_summary(
    outcomes: Iterable[object],
) -> MorningOperationSummary:
    items = tuple(outcomes)

    available = sum(
        getattr(item, "outcome_state", "") == "CLOSE_DATA_AVAILABLE"
        for item in items
    )

    pending = sum(
        getattr(item, "outcome_state", "") == "WAITING_FOR_CLOSE_DATA"
        for item in items
    )

    return MorningOperationSummary(
        candidate_count=len(items),
        recorded_count=sum(
            getattr(item, "observation_state", "") == "RECORDED"
            for item in items
        ),
        available_close_count=available,
        pending_close_count=pending,
        summary_state=(
            "GÜN SONU VERİSİ HAZIR"
            if available > 0
            else "KAPANIŞ VERİSİ BEKLENİYOR"
        ),
    )
