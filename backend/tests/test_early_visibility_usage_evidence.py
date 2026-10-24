from backend.app.analysis.ranking_visibility_context import (
    RankingVisibilityContext,
)

from backend.app.analysis.ranking_visibility_explanation import (
    build_visibility_explanation,
)


def test_early_visibility_usage_evidence_contract():
    context = RankingVisibilityContext(
        symbol="EVIDENCE",
        current_rank=45,
        previous_rank=160,
        rank_change=115,
        visibility_state="IMPROVING",
        zone_transition="YENI_TOP50",
        research_priority="HIGH",
    )

    result = build_visibility_explanation(context)

    assert result.symbol == "EVIDENCE"
    assert result.headline == "Görünürlük kazanıyor"
    assert result.rank_reason
    assert result.lifecycle_reason
    assert result.research_action
