from backend.app.analysis.early_visibility_tracking_bridge import (
    build_early_visibility_tracking_context,
)
from backend.app.workflow.early_visibility_task_adapter import (
    build_early_visibility_task_hint,
)
from backend.app.workflow.early_visibility_operation_adapter import (
    build_early_visibility_operation_item,
)


def test_ev12_3_operation_adapter():
    context = build_early_visibility_tracking_context(
        symbol="tuprs",
        visibility_state="IMPROVING",
        research_priority="HIGH",
    )

    task = build_early_visibility_task_hint(context)
    result = build_early_visibility_operation_item(task)

    assert result.symbol == "TUPRS"
    assert result.module == "Erken Görünürlük"
    assert result.priority == "HIGH"
