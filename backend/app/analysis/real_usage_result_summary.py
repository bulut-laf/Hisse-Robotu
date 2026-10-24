from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RealUsageResultSummary:
    candidate_count: int
    reviewed_count: int
    tracked_count: int
    completed_count: int
    usage_state: str


def build_real_usage_result_summary(
    *,
    candidate_count: int,
    reviewed_count: int,
    tracked_count: int,
    completed_count: int,
) -> RealUsageResultSummary:
    return RealUsageResultSummary(
        candidate_count=int(candidate_count),
        reviewed_count=int(reviewed_count),
        tracked_count=int(tracked_count),
        completed_count=int(completed_count),
        usage_state="GERÇEK KULLANIM ÖZETİ HAZIR",
    )
