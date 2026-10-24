from backend.app.workflow.research_memory_pattern_intelligence import (
    build_research_memory_pattern_state,
)


def test_ev15_sprint2_research_memory_pattern():
    result = build_research_memory_pattern_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.memory_state == "FOUNDATION"
    assert result.retrieval_state == "PREPARED"
    assert result.comparison_state == "OBSERVED"
    assert result.source == "EARLY_VISIBILITY"
