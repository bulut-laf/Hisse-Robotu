from backend.app.workflow.early_visibility_operational_context import (
    build_early_visibility_operational_context,
)


def test_ev13_2_operational_context():
    result = build_early_visibility_operational_context(
        symbol="tuprs",
        priority="high",
    )

    assert result.symbol == "TUPRS"
    assert result.task_type == "RESEARCH_REVIEW"
    assert result.priority == "HIGH"
    assert result.context == "OPERATIONAL_CONTEXT"
    assert result.source == "EARLY_VISIBILITY"
