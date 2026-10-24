from __future__ import annotations

from datetime import date

from backend.app.analysis.ranking_memory import (
    observations_from_research_rows,
    RankObservationJsonlStore,
)


def persist_research_rank_snapshot(
    *,
    rows,
    as_of: str | None = None,
    universe_source: str = "",
    profile_name: str = "",
    store=None,
) -> int:
    observations = observations_from_research_rows(
        rows=rows,
        as_of=as_of or date.today().isoformat(),
        universe_source=universe_source,
        profile_name=profile_name,
    )

    return (store or RankObservationJsonlStore()).append_snapshot(
        observations
    )
