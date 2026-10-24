from __future__ import annotations

from dataclasses import dataclass

from backend.app.workflow.early_visibility_operation_adapter import (
    EarlyVisibilityOperationItem,
)


@dataclass(frozen=True)
class EarlyVisibilitySurfaceItem:
    symbol: str
    label: str
    priority: str


def build_early_visibility_surface_item(
    operation: EarlyVisibilityOperationItem,
) -> EarlyVisibilitySurfaceItem:
    return EarlyVisibilitySurfaceItem(
        symbol=operation.symbol,
        label=operation.action,
        priority=operation.priority,
    )
