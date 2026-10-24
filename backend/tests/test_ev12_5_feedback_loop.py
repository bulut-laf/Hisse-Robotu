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
from backend.app.workflow.early_visibility_feedback_loop import (
    build_early_visibility_feedback_record,
)


def test_ev12_5_feedback_loop():
    context = build_early_visibility_tracking_context(
        symbol="tuprs",
        visibility_state="IMPROVING",
        research_priority="HIGH",
    )

    task = build_early_visibility_task_hint(context)
    operation = build_early_visibility_operation_item(task)
    surface = build_early_visibility_surface_item(operation)
    result = build_early_visibility_feedback_record(surface)

    assert result.symbol == "TUPRS"
    assert result.priority == "HIGH"
    assert result.source == "EARLY_VISIBILITY"
