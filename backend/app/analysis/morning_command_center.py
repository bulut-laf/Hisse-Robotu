from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MorningCommandCenter:
    candidate_count: int
    priority_count: int
    blocked_count: int
    pending_review_count: int
    state: str


def build_morning_command_center(
    *,
    candidates_count: int,
    priority_count: int,
    blocked_count: int,
    pending_review_count: int,
) -> MorningCommandCenter:
    return MorningCommandCenter(
        candidate_count=candidates_count,
        priority_count=priority_count,
        blocked_count=blocked_count,
        pending_review_count=pending_review_count,
        state=(
            "SABAH OPERASYON HAZIR"
            if candidates_count > 0
            else "ADAY BEKLENİYOR"
        ),
    )
