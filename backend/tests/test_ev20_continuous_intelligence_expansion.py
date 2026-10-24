from backend.app.workflow.continuous_intelligence_expansion import (
    build_continuous_intelligence_expansion_state,
)


def test_ev20_continuous_intelligence_expansion():
    result = build_continuous_intelligence_expansion_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.expansion_state == "TRACKING"
    assert result.intelligence_state == "EVOLVING"
    assert result.foundation_state == "READY"
    assert result.source == "EARLY_VISIBILITY"
