from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MorningFlowContext:
    snapshot_available: bool
    refresh_required: bool


def build_morning_flow_context(
    *,
    snapshot_available: bool,
    refresh_required: bool,
) -> MorningFlowContext:
    return MorningFlowContext(
        snapshot_available=snapshot_available,
        refresh_required=refresh_required,
    )
