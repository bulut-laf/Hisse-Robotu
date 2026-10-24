from backend.app.workflow.adaptive_research_final_lock import (
    build_adaptive_research_final_lock,
)


def test_ev15_final_adaptive_research_lock():
    result = build_adaptive_research_final_lock("tuprs")

    assert result.symbol == "TUPRS"
    assert result.workflow_state == "LOCKED"
    assert result.memory_state == "CONNECTED"
    assert result.optimization_state == "PREPARED"
    assert result.readiness_state == "READY"
    assert result.source == "EARLY_VISIBILITY"
