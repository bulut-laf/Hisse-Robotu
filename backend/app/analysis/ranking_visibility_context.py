from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.app.analysis.ranking_memory import RankObservation
from backend.app.analysis.ranking_trajectory import build_rank_trajectories


@dataclass(frozen=True)
class RankingVisibilityContext:
    symbol: str
    current_rank: int
    previous_rank: int | None
    rank_change: int
    visibility_state: str
    zone_transition: str | None
    research_priority: str
    quality_status: str | None = None
    data_blocked: bool = False


def build_visibility_context_from_trajectory(
    observations: Iterable[RankObservation],
) -> tuple[RankingVisibilityContext, ...]:
    trajectories = build_rank_trajectories(observations)

    results = []

    for item in trajectories:
        gain = item.gain_3s or item.gain_1s or 0

        if gain > 0:
            state = "IMPROVING"
        elif gain < 0:
            state = "WEAKENING"
        else:
            state = "STABLE"

        priority = (
            "HIGH"
            if gain >= 20
            else "MEDIUM"
            if gain > 0
            else "NORMAL"
        )

        results.append(
            RankingVisibilityContext(
                symbol=item.symbol,
                current_rank=item.current_rank,
                previous_rank=item.rank_3s,
                rank_change=gain,
                visibility_state=state,
                zone_transition=(
                    item.zone_events[0]
                    if item.zone_events
                    else None
                ),
                research_priority=priority,
            )
        )

    return tuple(results)

from backend.app.analysis.ranking_quality_context import EarlyVisibilityQualityContext


def attach_quality_context(
    visibility: RankingVisibilityContext,
    quality: EarlyVisibilityQualityContext | None,
) -> RankingVisibilityContext:
    return RankingVisibilityContext(
        symbol=visibility.symbol,
        current_rank=visibility.current_rank,
        previous_rank=visibility.previous_rank,
        rank_change=visibility.rank_change,
        visibility_state=visibility.visibility_state,
        zone_transition=visibility.zone_transition,
        research_priority=(
            "NORMAL"
            if quality is not None and (
                quality.data_blocked
                or quality.status in ("ZAYIF", "TEYITSIZ")
            )
            else visibility.research_priority
        ),
        quality_status=(
            quality.status
            if quality is not None
            else None
        ),
        data_blocked=(
            quality.data_blocked
            if quality is not None
            else False
        ),
    )




