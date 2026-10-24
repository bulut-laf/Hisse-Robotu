from backend.app.analysis.early_visibility_tracking_bridge import (
    build_early_visibility_tracking_context,
)
from backend.app.workflow.early_visibility_task_adapter import (
    build_early_visibility_task_hint,
)


def test_ev12_2_early_visibility_task_adapter():
    context = build_early_visibility_tracking_context(
        symbol="tuprs",
        visibility_state="IMPROVING",
        research_priority="HIGH",
    )

    result = build_early_visibility_task_hint(context)

    assert result.symbol == "TUPRS"
    assert result.target_module == "Erken Görünürlük"
    assert result.research_priority == "HIGH"
