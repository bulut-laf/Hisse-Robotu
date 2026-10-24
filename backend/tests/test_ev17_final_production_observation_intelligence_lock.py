from backend.app.workflow.production_observation_intelligence_lock import (
    build_production_observation_intelligence_lock,
)


def test_ev17_final_production_observation_intelligence_lock():
    result = build_production_observation_intelligence_lock("tuprs")

    assert result.symbol == "TUPRS"
    assert result.observation_state == "LOCKED"
    assert result.quality_state == "LOCKED"
    assert result.feedback_state == "CONNECTED"
    assert result.readiness_state == "READY"
    assert result.source == "EARLY_VISIBILITY"
