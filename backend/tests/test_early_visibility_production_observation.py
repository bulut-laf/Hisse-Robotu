from backend.app.workflow.early_visibility_production_observation import (
    build_early_visibility_production_observation,
)


def test_early_visibility_production_observation():
    result = build_early_visibility_production_observation("tuprs")

    assert result.symbol == "TUPRS"
    assert result.mode_state == "PRODUCTION_OBSERVATION"
    assert result.observation_state == "ACTIVE"
    assert result.feedback_state == "COLLECTING"
    assert result.source == "EARLY_VISIBILITY"
