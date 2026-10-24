from backend.app.workflow.continuous_optimization_loop import (
    build_continuous_optimization_loop_state,
)


def test_ev18_sprint3_continuous_optimization_loop():
    result = build_continuous_optimization_loop_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.feedback_state == "CONNECTED"
    assert result.mapping_state == "TRACKING"
    assert result.calibration_state == "ACTIVE"
    assert result.maturity_state == "FOUNDATION"
    assert result.source == "EARLY_VISIBILITY"
