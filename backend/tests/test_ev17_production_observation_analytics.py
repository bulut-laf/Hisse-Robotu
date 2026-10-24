from backend.app.workflow.production_observation_analytics import (
    build_production_observation_analytics_state,
)


def test_ev17_production_observation_analytics():
    result = build_production_observation_analytics_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.observation_state == "ACTIVE"
    assert result.quality_state == "TRACKING"
    assert result.analytics_state == "FOUNDATION"
    assert result.source == "EARLY_VISIBILITY"
