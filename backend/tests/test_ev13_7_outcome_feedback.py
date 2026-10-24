from backend.app.workflow.early_visibility_outcome_feedback import (
    build_early_visibility_outcome_feedback,
)


def test_ev13_7_outcome_feedback():
    result = build_early_visibility_outcome_feedback(
        "tuprs",
        "RECORDED",
    )

    assert result.symbol == "TUPRS"
    assert result.outcome == "RECORDED"
    assert result.feedback_state == "RECORDED"
    assert result.source == "EARLY_VISIBILITY"
