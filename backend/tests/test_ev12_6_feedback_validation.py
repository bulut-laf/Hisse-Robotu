from backend.app.workflow.early_visibility_feedback_validation import (
    validate_early_visibility_feedback,
)


class DummyRecord:
    symbol = "TUPRS"
    priority = "HIGH"
    source = "EARLY_VISIBILITY"


def test_ev12_6_feedback_validation():
    result = validate_early_visibility_feedback(DummyRecord())

    assert result.symbol == "TUPRS"
    assert result.valid is True
    assert result.source == "EARLY_VISIBILITY"
