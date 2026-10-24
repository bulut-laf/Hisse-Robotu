from backend.app.workflow.production_intelligence_feedback_loop import (
    build_production_intelligence_feedback_state,
)


def test_ev17_sprint3_production_intelligence_feedback_loop():
    result = build_production_intelligence_feedback_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.feedback_state == "COLLECTING"
    assert result.improvement_state == "MAPPED"
    assert result.calibration_state == "TRACKING"
    assert result.source == "EARLY_VISIBILITY"
