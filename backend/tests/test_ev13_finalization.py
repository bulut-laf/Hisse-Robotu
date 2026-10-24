from backend.app.workflow.early_visibility_finalization import (
    finalize_early_visibility_flow,
)


def test_ev13_finalization():
    result = finalize_early_visibility_flow("tuprs")

    assert result.symbol == "TUPRS"
    assert result.feedback_quality == "VALIDATED"
    assert result.observation_linked is True
    assert result.lifecycle_status == "CLOSED"
    assert result.source == "EARLY_VISIBILITY"
