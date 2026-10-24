from backend.app.workflow.long_term_intelligence_layer import (
    build_long_term_intelligence_state,
)


def test_ev16_sprint1_long_term_intelligence():
    result = build_long_term_intelligence_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.memory_state == "FOUNDATION"
    assert result.historical_state == "PREPARED"
    assert result.persistence_state == "FOUNDATION"
    assert result.source == "EARLY_VISIBILITY"
