from backend.app.workflow.continuous_intelligence_optimization import (
    build_continuous_intelligence_optimization_state,
)


def test_ev18_sprint1_continuous_intelligence_optimization():
    result = build_continuous_intelligence_optimization_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.observation_state == "ACTIVE"
    assert result.improvement_state == "TRACKING"
    assert result.optimization_state == "FOUNDATION"
    assert result.source == "EARLY_VISIBILITY"
