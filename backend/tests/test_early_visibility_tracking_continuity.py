from backend.app.analysis.early_visibility_tracking_bridge import (
    build_early_visibility_tracking_context,
)


def test_early_visibility_tracking_context():
    result = build_early_visibility_tracking_context(
        symbol="TEST",
        visibility_state="IMPROVING",
        research_priority="HIGH",
    )

    assert result.symbol == "TEST"
    assert result.visibility_state == "IMPROVING"
    assert result.research_priority == "HIGH"
    assert result.source == "EARLY_VISIBILITY"