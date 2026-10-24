from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class V1ReleaseCandidateGate:
    regression_passed: bool
    operation_ready: bool
    user_flow_ready: bool
    release_state: str


def build_v1_release_candidate_gate(
    *,
    regression_passed: bool,
    operation_ready: bool,
    user_flow_ready: bool,
) -> V1ReleaseCandidateGate:
    ready = (
        bool(regression_passed)
        and bool(operation_ready)
        and bool(user_flow_ready)
    )

    return V1ReleaseCandidateGate(
        regression_passed=bool(regression_passed),
        operation_ready=bool(operation_ready),
        user_flow_ready=bool(user_flow_ready),
        release_state=(
            "V1 RELEASE CANDIDATE HAZIR"
            if ready
            else "V1 FINAL KONTROL BEKLİYOR"
        ),
    )
