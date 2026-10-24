from backend.app.analysis.ranking_visibility_context import (
    RankingVisibilityContext,
)

from backend.app.analysis.ranking_visibility_explanation import (
    build_visibility_explanation,
)


def test_visibility_usage_surface_explanation():
    context = RankingVisibilityContext(
        symbol="TEST",
        current_rank=50,
        previous_rank=100,
        rank_change=50,
        visibility_state="IMPROVING",
        zone_transition="YENI_TOP50",
        research_priority="HIGH",
    )

    result = build_visibility_explanation(context)

    assert result.symbol == "TEST"
    assert result.headline == "Görünürlük kazanıyor"
    assert result.research_action == "Ana Research Sıralaması"
