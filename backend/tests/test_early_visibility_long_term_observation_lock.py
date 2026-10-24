from backend.app.analysis.ranking_visibility_context import (
    RankingVisibilityContext,
)

from backend.app.analysis.ranking_visibility_explanation import (
    build_visibility_explanation,
)


def test_early_visibility_long_term_observation_lock():
    contexts = (
        RankingVisibilityContext(
            symbol="LOCK",
            current_rank=180,
            previous_rank=250,
            rank_change=70,
            visibility_state="IMPROVING",
            zone_transition=None,
            research_priority="MEDIUM",
        ),
        RankingVisibilityContext(
            symbol="LOCK",
            current_rank=60,
            previous_rank=180,
            rank_change=120,
            visibility_state="IMPROVING",
            zone_transition="YENI_TOP100",
            research_priority="HIGH",
        ),
    )

    first = build_visibility_explanation(contexts[0])
    second = build_visibility_explanation(contexts[1])

    assert first.symbol == second.symbol
    assert second.rank_reason
    assert second.lifecycle_reason
    assert second.research_action
