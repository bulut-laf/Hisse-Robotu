from backend.app.workflow.production_intelligence_observation import (
    build_production_intelligence_observation,
)


def test_ev14_sprint1_production_intelligence():
    result = build_production_intelligence_observation("tuprs")

    assert result.symbol == "TUPRS"
    assert result.usage_state == "OBSERVED"
    assert result.quality_state == "TRACKING"
    assert result.source == "EARLY_VISIBILITY"
