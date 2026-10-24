from backend.app.analysis.early_visibility_tracking_bridge import (
    build_early_visibility_tracking_context,
)
from backend.app.workflow.early_visibility_task_adapter import (
    build_early_visibility_task_hint,
)
from backend.app.workflow.early_visibility_operation_adapter import (
    build_early_visibility_operation_item,
)
from backend.app.workflow.early_visibility_surface_adapter import (
    build_early_visibility_surface_item,
)


def test_ev12_4_surface_adapter():
    context = build_early_visibility_tracking_context(
        symbol="tuprs",
        visibility_state="IMPROVING",
        research_priority="HIGH",
    )

    task = build_early_visibility_task_hint(context)
    operation = build_early_visibility_operation_item(task)
    result = build_early_visibility_surface_item(operation)

    assert result.symbol == "TUPRS"
    assert result.priority == "HIGH"
