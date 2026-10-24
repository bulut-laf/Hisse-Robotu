from backend.app.workflow.production_quality_analytics import (
    build_production_quality_analytics_state,
)


def test_ev17_sprint2_production_quality_analytics():
    result = build_production_quality_analytics_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.false_positive_state == "TRACKING"
    assert result.accuracy_state == "OBSERVED"
    assert result.outcome_state == "MEASURED"
    assert result.metric_state == "FOUNDATION"
    assert result.source == "EARLY_VISIBILITY"
