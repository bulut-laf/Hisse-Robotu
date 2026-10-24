from backend.app.workflow.advanced_optimization_block import (
    build_advanced_optimization_state,
)


def test_ev25_ev27_advanced_optimization_block():
    result = build_advanced_optimization_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.optimization_state == "TRACKING"
    assert result.prediction_state == "FOUNDATION"
    assert result.quality_state == "EXPANDING"
    assert result.source == "EARLY_VISIBILITY"
