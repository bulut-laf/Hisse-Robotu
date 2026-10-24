from backend.app.workflow.early_visibility_task_engine_bridge import (
    build_early_visibility_task_bridge,
)


def test_ev13_1_task_engine_bridge():
    result = build_early_visibility_task_bridge(
        symbol="tuprs",
        priority="high",
    )

    assert result.symbol == "TUPRS"
    assert result.task_type == "RESEARCH_REVIEW"
    assert result.priority == "HIGH"
    assert result.source == "EARLY_VISIBILITY"
