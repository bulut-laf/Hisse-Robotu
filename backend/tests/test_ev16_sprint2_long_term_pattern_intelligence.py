from backend.app.workflow.long_term_pattern_intelligence import (
    build_long_term_pattern_intelligence_state,
)


def test_ev16_sprint2_long_term_pattern_intelligence():
    result = build_long_term_pattern_intelligence_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.historical_case_state == "PREPARED"
    assert result.cross_period_state == "OBSERVED"
    assert result.pattern_state == "FOUNDATION"
    assert result.source == "EARLY_VISIBILITY"
