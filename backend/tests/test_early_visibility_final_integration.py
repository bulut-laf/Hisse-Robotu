from backend.app.analysis.ranking_visibility_context import (
    RankingVisibilityContext,
)

from backend.app.analysis.ranking_visibility_explanation import (
    build_visibility_explanation,
)


def test_final_visibility_integration_contract():
    context = RankingVisibilityContext(
        symbol="TEST",
        current_rank=20,
        previous_rank=120,
        rank_change=100,
        visibility_state="IMPROVING",
        zone_transition="YENI_TOP30",
        research_priority="HIGH",
    )

    result = build_visibility_explanation(context)

    assert result.symbol == "TEST"
    assert result.headline == "Görünürlük kazanıyor"
    assert result.rank_reason
    assert result.lifecycle_reason
    assert result.quality_reason
    assert result.research_action
