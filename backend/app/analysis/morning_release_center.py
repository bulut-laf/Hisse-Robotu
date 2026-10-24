from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MorningReleaseCenter:
    market_state: str
    candidate_count: int
    priority_count: int
    pending_action_count: int
    release_state: str


def build_morning_release_center(
    *,
    market_state: str,
    candidate_count: int,
    priority_count: int,
    pending_action_count: int,
) -> MorningReleaseCenter:
    return MorningReleaseCenter(
        market_state=str(market_state),
        candidate_count=int(candidate_count),
        priority_count=int(priority_count),
        pending_action_count=int(pending_action_count),
        release_state=(
            "V1 SABAH OPERASYONU HAZIR"
            if candidate_count > 0
            else "ADAY BEKLENİYOR"
        ),
    )
