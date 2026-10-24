from backend.app.workflow.long_term_intelligence_optimization import (
    build_long_term_intelligence_optimization_state,
)


def test_ev16_sprint3_long_term_intelligence_optimization():
    result = build_long_term_intelligence_optimization_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.learning_state == "FOUNDATION"
    assert result.improvement_state == "TRACKING"
    assert result.knowledge_state == "EVOLVING"
    assert result.readiness_state == "PREPARED"
    assert result.source == "EARLY_VISIBILITY"
