from backend.app.workflow.early_visibility_task_completion import (
    complete_early_visibility_task,
)


def test_ev13_5_task_completion():
    result = complete_early_visibility_task("tuprs")

    assert result.symbol == "TUPRS"
    assert result.state == "COMPLETED"
    assert result.completed is True
    assert result.task_type == "RESEARCH_REVIEW"
    assert result.source == "EARLY_VISIBILITY"
