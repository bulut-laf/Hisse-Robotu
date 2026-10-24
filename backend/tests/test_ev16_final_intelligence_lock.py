from backend.app.workflow.final_intelligence_lock import (
    build_final_intelligence_lock,
)


def test_ev16_final_intelligence_lock():
    result = build_final_intelligence_lock("tuprs")

    assert result.symbol == "TUPRS"
    assert result.memory_state == "LOCKED"
    assert result.pattern_state == "CONNECTED"
    assert result.learning_state == "READY"
    assert result.readiness_state == "PRODUCTION_READY"
    assert result.source == "EARLY_VISIBILITY"
