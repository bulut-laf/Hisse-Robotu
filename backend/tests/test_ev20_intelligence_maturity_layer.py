from backend.app.workflow.intelligence_maturity_layer import (
    build_intelligence_maturity_state,
)


def test_ev20_intelligence_maturity_layer():
    result = build_intelligence_maturity_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.maturity_state == "TRACKING"
    assert result.optimization_state == "ACTIVE"
    assert result.quality_state == "OBSERVED"
    assert result.readiness_state == "PREPARED"
    assert result.source == "EARLY_VISIBILITY"
