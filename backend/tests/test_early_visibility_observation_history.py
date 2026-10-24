from backend.app.analysis.ranking_visibility_context import (
    RankingVisibilityContext,
)

from backend.app.analysis.ranking_visibility_explanation import (
    build_visibility_explanation,
)


def test_visibility_observation_history_keeps_state_transition_context():
    first = RankingVisibilityContext(
        symbol="TEST",
        current_rank=200,
        previous_rank=250,
        rank_change=50,
        visibility_state="IMPROVING",
        zone_transition=None,
        research_priority="MEDIUM",
    )

    second = RankingVisibilityContext(
        symbol="TEST",
        current_rank=80,
        previous_rank=200,
        rank_change=120,
        visibility_state="IMPROVING",
        zone_transition="YENI_TOP100",
        research_priority="HIGH",
    )

    first_result = build_visibility_explanation(first)
    second_result = build_visibility_explanation(second)

    assert first_result.symbol == second_result.symbol
    assert first_result.headline == second_result.headline
    assert second.zone_transition == "YENI_TOP100"
    assert second.rank_change > first.rank_change
