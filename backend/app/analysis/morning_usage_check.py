from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MorningUsageCheck:
    snapshot_ready: bool
    candidate_flow_ready: bool
    status: str


def check_morning_usage(
    *,
    snapshot_ready: bool,
    candidate_flow_ready: bool,
) -> MorningUsageCheck:
    if snapshot_ready and candidate_flow_ready:
        return MorningUsageCheck(True, True, "READY")

    return MorningUsageCheck(
        snapshot_ready,
        candidate_flow_ready,
        "WAITING",
    )
