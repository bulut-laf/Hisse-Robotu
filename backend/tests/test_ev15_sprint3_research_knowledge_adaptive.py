from backend.app.workflow.research_knowledge_adaptive_optimization import (
    build_research_knowledge_adaptive_state,
)


def test_ev15_sprint3_research_knowledge_adaptive():
    result = build_research_knowledge_adaptive_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.knowledge_state == "FOUNDATION"
    assert result.priority_state == "IMPROVING"
    assert result.optimization_state == "PREPARED"
    assert result.source == "EARLY_VISIBILITY"
