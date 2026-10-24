from backend.app.workflow.intelligence_evolution_block import (
    build_intelligence_evolution_state,
)


def test_ev19_intelligence_evolution_block():
    result = build_intelligence_evolution_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.evolution_state == "TRACKING"
    assert result.adaptation_state == "FOUNDATION"
    assert result.readiness_state == "PREPARED"
    assert result.source == "EARLY_VISIBILITY"
