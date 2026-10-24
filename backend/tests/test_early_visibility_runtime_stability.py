from backend.app.analysis.ranking_visibility_context import (
    RankingVisibilityContext,
)

from backend.app.analysis.ranking_visibility_explanation import (
    build_visibility_explanation,
)


def test_early_visibility_runtime_stability_contract():
    context = RankingVisibilityContext(
        symbol="STABLE",
        current_rank=35,
        previous_rank=110,
        rank_change=75,
        visibility_state="IMPROVING",
        zone_transition="YENI_TOP50",
        research_priority="HIGH",
    )

    result = build_visibility_explanation(context)

    assert result.symbol == "STABLE"
    assert result.headline
    assert result.rank_reason
    assert result.research_action
