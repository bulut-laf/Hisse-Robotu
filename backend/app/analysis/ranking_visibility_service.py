from __future__ import annotations

from backend.app.analysis.ranking_memory import RankObservationJsonlStore
from backend.app.analysis.ranking_visibility_context import (
    build_visibility_context_from_trajectory,
)


def build_current_visibility_context(
    *,
    store: RankObservationJsonlStore | None = None,
):
    memory = store or RankObservationJsonlStore()
    observations = memory.list()

    return build_visibility_context_from_trajectory(observations)
