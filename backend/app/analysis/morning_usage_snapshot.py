from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class MorningUsageSnapshot:
    candidate_count: int
    priority_count: int
    reviewed_count: int
    pending_review_count: int
    usage_state: str


def build_morning_usage_snapshot(
    candidates: Iterable[object],
    feedback_items: Iterable[object] = (),
) -> MorningUsageSnapshot:
    candidate_list = tuple(candidates)
    feedback_list = tuple(feedback_items)

    reviewed = sum(
        str(getattr(item, "user_state", "")).casefold()
        in {"incelendi", "işlem yapıldı", "pas geçildi"}
        for item in feedback_list
    )

    return MorningUsageSnapshot(
        candidate_count=len(candidate_list),
        priority_count=sum(
            getattr(item, "research_priority", "") == "HIGH"
            for item in candidate_list
        ),
        reviewed_count=reviewed,
        pending_review_count=max(
            0,
            len(candidate_list) - reviewed,
        ),
        usage_state=(
            "GÜNLÜK OPERASYON AKTİF"
            if candidate_list
            else "ADAY BEKLENİYOR"
        ),
    )
