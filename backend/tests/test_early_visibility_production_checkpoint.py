from backend.app.analysis.ranking_visibility_context import (
    RankingVisibilityContext,
)

from backend.app.analysis.ranking_visibility_explanation import (
    build_visibility_explanation,
)


def test_early_visibility_production_checkpoint():
    context = RankingVisibilityContext(
        symbol="PROD",
        current_rank=10,
        previous_rank=80,
        rank_change=70,
        visibility_state="IMPROVING",
        zone_transition="YENI_TOP30",
        research_priority="HIGH",
    )

    result = build_visibility_explanation(context)

    assert result.symbol == "PROD"
    assert result.headline == "Görünürlük kazanıyor"
    assert result.research_action == "Ana Research Sıralaması"
