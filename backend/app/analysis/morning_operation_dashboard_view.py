from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class MorningOperationDashboardView:
    candidate_count: int
    high_priority_count: int
    blocked_count: int
    user_review_pending: int
    dashboard_state: str


def build_morning_operation_dashboard_view(
    candidates: Iterable[object],
    feedback_items: Iterable[object] = (),
) -> MorningOperationDashboardView:
    candidate_list = tuple(candidates)
    feedback_list = tuple(feedback_items)

    return MorningOperationDashboardView(
        candidate_count=len(candidate_list),
        high_priority_count=sum(
            getattr(item, "research_priority", "") == "HIGH"
            for item in candidate_list
        ),
        blocked_count=sum(
            bool(getattr(item, "data_blocked", False))
            for item in candidate_list
        ),
        user_review_pending=max(
            0,
            len(candidate_list) - len(feedback_list),
        ),
        dashboard_state=(
            "OPERASYON HAZIR"
            if candidate_list
            else "ADAY BEKLENİYOR"
        ),
    )
