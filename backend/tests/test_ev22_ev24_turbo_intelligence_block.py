from backend.app.workflow.ev22_ev24_turbo_intelligence_block import (
    build_turbo_intelligence_evolution_state,
)


def test_ev22_ev24_turbo_intelligence_block():
    result = build_turbo_intelligence_evolution_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.cycle_state == "EXPANDED"
    assert result.optimization_state == "ACTIVE"
    assert result.evolution_state == "TRACKING"
    assert result.readiness_state == "PREPARED"
    assert result.source == "EARLY_VISIBILITY"
