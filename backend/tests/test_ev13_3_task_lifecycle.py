from backend.app.workflow.early_visibility_task_lifecycle import (
    build_early_visibility_task_lifecycle,
)


def test_ev13_3_task_lifecycle():
    result = build_early_visibility_task_lifecycle("tuprs")

    assert result.symbol == "TUPRS"
    assert result.state == "CREATED"
    assert result.task_type == "RESEARCH_REVIEW"
    assert result.source == "EARLY_VISIBILITY"
