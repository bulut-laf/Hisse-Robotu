from backend.app.analysis.ranking_visibility_context import (
    RankingVisibilityContext,
)

from backend.app.analysis.ranking_visibility_explanation import (
    build_visibility_explanation,
)


def test_cross_surface_visibility_consistency():
    context = RankingVisibilityContext(
        symbol="TUPRS",
        current_rank=40,
        previous_rank=120,
        rank_change=80,
        visibility_state="IMPROVING",
        zone_transition="YENI_TOP50",
        research_priority="HIGH",
    )

    explanation = build_visibility_explanation(context)

    assert explanation.symbol == "TUPRS"
    assert explanation.headline == "Görünürlük kazanıyor"
    assert "iyileşme" in explanation.rank_reason
    assert explanation.research_action == "Ana Research Sıralaması"
