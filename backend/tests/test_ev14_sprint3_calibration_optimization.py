from backend.app.workflow.intelligence_calibration_optimization import (
    build_intelligence_calibration_state,
)


def test_ev14_sprint3_calibration_optimization():
    result = build_intelligence_calibration_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.calibration_state == "TRACKING"
    assert result.historical_state == "PREPARED"
    assert result.quality_trend == "OBSERVED"
    assert result.source == "EARLY_VISIBILITY"
