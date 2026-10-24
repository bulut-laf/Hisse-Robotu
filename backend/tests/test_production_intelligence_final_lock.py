from backend.app.workflow.production_intelligence_final_lock import (
    build_production_intelligence_final_lock,
)


def test_production_intelligence_final_lock():
    result = build_production_intelligence_final_lock("tuprs")

    assert result.symbol == "TUPRS"
    assert result.intelligence_state == "LOCKED"
    assert result.observation_state == "ACTIVE"
    assert result.optimization_state == "STABLE"
    assert result.readiness_state == "READY"
    assert result.source == "EARLY_VISIBILITY"
