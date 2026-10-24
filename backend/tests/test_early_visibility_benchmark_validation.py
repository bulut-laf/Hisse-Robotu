from backend.app.analysis.ranking_visibility_context import (
    RankingVisibilityContext,
)

from backend.app.analysis.ranking_visibility_explanation import (
    build_visibility_explanation,
)


def test_visibility_benchmark_validation_preserves_observed_context():
    context = RankingVisibilityContext(
        symbol="TEST",
        current_rank=25,
        previous_rank=120,
        rank_change=95,
        visibility_state="IMPROVING",
        zone_transition="YENI_TOP30",
        research_priority="HIGH",
    )

    result = build_visibility_explanation(context)

    assert result.symbol == "TEST"
    assert result.headline == "Görünürlük kazanıyor"
    assert "iyileşme" in result.rank_reason
    assert result.research_action == "Ana Research Sıralaması"
