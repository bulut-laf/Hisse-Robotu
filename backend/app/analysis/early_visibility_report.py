from __future__ import annotations

from dataclasses import asdict
from backend.app.analysis.ranking_visibility_context import RankingVisibilityContext


def build_early_visibility_report(
    contexts: tuple[RankingVisibilityContext, ...],
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "symbol": item.symbol,
            "current_rank": item.current_rank,
            "previous_rank": item.previous_rank,
            "rank_change": item.rank_change,
            "visibility_state": item.visibility_state,
            "zone_transition": item.zone_transition,
            "research_priority": item.research_priority,
            "quality_status": item.quality_status,
            "data_blocked": item.data_blocked,
        }
        for item in contexts
    )

