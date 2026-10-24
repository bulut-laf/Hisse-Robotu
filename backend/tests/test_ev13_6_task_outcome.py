from backend.app.workflow.early_visibility_task_outcome import (
    record_early_visibility_task_outcome,
)

def test_ev13_6_task_outcome():
    result = record_early_visibility_task_outcome("tuprs")

    assert result.symbol == "TUPRS"
    assert result.outcome == "RECORDED"
    assert result.task_type == "RESEARCH_REVIEW"
    assert result.source == "EARLY_VISIBILITY"
