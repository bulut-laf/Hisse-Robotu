from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MorningWorkflowClosure:
    reviewed_count: int
    pending_count: int
    tracked_count: int
    closure_state: str


def build_morning_workflow_closure(
    *,
    reviewed_count: int,
    pending_count: int,
    tracked_count: int,
) -> MorningWorkflowClosure:
    return MorningWorkflowClosure(
        reviewed_count=int(reviewed_count),
        pending_count=int(pending_count),
        tracked_count=int(tracked_count),
        closure_state="SABAH OPERASYON AKIŞI TAMAMLANDI",
    )
