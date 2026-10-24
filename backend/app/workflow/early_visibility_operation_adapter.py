from __future__ import annotations

from dataclasses import dataclass

from backend.app.workflow.early_visibility_task_adapter import (
    EarlyVisibilityTaskHint,
)


@dataclass(frozen=True)
class EarlyVisibilityOperationItem:
    symbol: str
    action: str
    module: str
    priority: str


def build_early_visibility_operation_item(
    task: EarlyVisibilityTaskHint,
) -> EarlyVisibilityOperationItem:
    return EarlyVisibilityOperationItem(
        symbol=task.symbol,
        action=task.title,
        module=task.target_module,
        priority=task.research_priority,
    )
