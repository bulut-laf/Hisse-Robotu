from backend.app.analysis.ranking_visibility_context import (
    RankingVisibilityContext,
)

from backend.app.analysis.ranking_visibility_explanation import (
    build_visibility_explanation,
)


def test_early_visibility_regression_lock_contract():
    context = RankingVisibilityContext(
        symbol="LOCK",
        current_rank=15,
        previous_rank=90,
        rank_change=75,
        visibility_state="IMPROVING",
        zone_transition="YENI_TOP30",
        research_priority="HIGH",
    )

    result = build_visibility_explanation(context)

    assert result.symbol == "LOCK"
    assert result.headline == "Görünürlük kazanıyor"
    assert result.rank_reason == (
        "Araştırma sıralamasında iyileşme görülüyor."
    )
    assert result.research_action == "Ana Research Sıralaması"
