from backend.app.analysis.ranking_visibility_context import (
    RankingVisibilityContext,
)

from backend.app.analysis.ranking_visibility_explanation import (
    build_visibility_explanation,
)


def test_visibility_outcome_comparison_keeps_observation_separate():
    context = RankingVisibilityContext(
        symbol="TEST",
        current_rank=30,
        previous_rank=150,
        rank_change=120,
        visibility_state="IMPROVING",
        zone_transition="YENI_TOP30",
        research_priority="HIGH",
    )

    result = build_visibility_explanation(context)

    assert result.symbol == "TEST"
    assert result.headline == "Görünürlük kazanıyor"
    assert result.research_action == "Ana Research Sıralaması"
