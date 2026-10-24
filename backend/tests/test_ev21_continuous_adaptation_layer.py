from backend.app.workflow.continuous_adaptation_layer import (
    build_continuous_adaptation_state,
)


def test_ev21_continuous_adaptation_layer():
    result = build_continuous_adaptation_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.adaptation_state == "TRACKING"
    assert result.refinement_state == "ACTIVE"
    assert result.optimization_bridge_state == "PREPARED"
    assert result.source == "EARLY_VISIBILITY"
