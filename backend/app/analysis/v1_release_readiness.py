from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class V1ReleaseReadiness:
    regression_passed: bool
    morning_flow_ready: bool
    operation_cycle_ready: bool
    readiness_state: str


def build_v1_release_readiness(
    *,
    regression_passed: bool,
    morning_flow_ready: bool,
    operation_cycle_ready: bool,
) -> V1ReleaseReadiness:
    ready = (
        regression_passed
        and morning_flow_ready
        and operation_cycle_ready
    )

    return V1ReleaseReadiness(
        regression_passed=bool(regression_passed),
        morning_flow_ready=bool(morning_flow_ready),
        operation_cycle_ready=bool(operation_cycle_ready),
        readiness_state=(
            "V1 RELEASE HAZIR"
            if ready
            else "V1 HAZIRLIK DEVAM EDİYOR"
        ),
    )
