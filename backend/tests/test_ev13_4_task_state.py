from backend.app.workflow.early_visibility_task_state import (
    build_early_visibility_task_state,
)


def test_ev13_4_task_state():
    result = build_early_visibility_task_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.state == "CREATED"
    assert result.task_type == "RESEARCH_REVIEW"
    assert result.source == "EARLY_VISIBILITY"
