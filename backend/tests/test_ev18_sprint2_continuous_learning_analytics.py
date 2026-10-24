from backend.app.workflow.continuous_learning_analytics import (
    build_continuous_learning_analytics_state,
)


def test_ev18_sprint2_continuous_learning_analytics():
    result = build_continuous_learning_analytics_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.pattern_state == "OBSERVED"
    assert result.feedback_metric_state == "FOUNDATION"
    assert result.learning_state == "TRACKING"
    assert result.evolution_state == "PREPARED"
    assert result.source == "EARLY_VISIBILITY"
