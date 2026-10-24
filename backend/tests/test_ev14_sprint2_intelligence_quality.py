from backend.app.workflow.intelligence_quality_layer import (
    build_intelligence_quality_observation,
)


def test_ev14_sprint2_intelligence_quality():
    result = build_intelligence_quality_observation("tuprs")

    assert result.symbol == "TUPRS"
    assert result.false_positive_state == "OBSERVED"
    assert result.metric_state == "TRACKING"
    assert result.calibration_state == "FOUNDATION"
    assert result.source == "EARLY_VISIBILITY"
