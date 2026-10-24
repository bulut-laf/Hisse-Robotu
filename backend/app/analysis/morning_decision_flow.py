from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MorningDecisionFlow:
    candidate_count: int
    inspect_count: int
    blocked_count: int
    decision_state: str


def build_morning_decision_flow(
    candidates: tuple[object, ...],
) -> MorningDecisionFlow:
    return MorningDecisionFlow(
        candidate_count=len(candidates),
        inspect_count=sum(
            not bool(getattr(item, "data_blocked", False))
            for item in candidates
        ),
        blocked_count=sum(
            bool(getattr(item, "data_blocked", False))
            for item in candidates
        ),
        decision_state=(
            "İNCELEMEYE HAZIR"
            if candidates
            else "ADAY YOK"
        ),
    )
