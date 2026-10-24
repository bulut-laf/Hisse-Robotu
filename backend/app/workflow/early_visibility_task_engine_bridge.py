from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EarlyVisibilityTaskBridgeResult:
    symbol: str
    task_type: str
    priority: str
    source: str = "EARLY_VISIBILITY"


def build_early_visibility_task_bridge(
    symbol: str,
    priority: str,
) -> EarlyVisibilityTaskBridgeResult:
    return EarlyVisibilityTaskBridgeResult(
        symbol=str(symbol).upper(),
        task_type="RESEARCH_REVIEW",
        priority=str(priority).upper(),
    )
