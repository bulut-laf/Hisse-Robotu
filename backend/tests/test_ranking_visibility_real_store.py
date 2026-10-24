from pathlib import Path

from backend.app.analysis.ranking_memory import (
    RankObservation,
    RankObservationJsonlStore,
)
from backend.app.analysis.ranking_visibility_service import (
    build_current_visibility_context,
)


def test_visibility_service_reads_jsonl_store(tmp_path):
    store_path = tmp_path / "rank_observations.jsonl"

    store = RankObservationJsonlStore(path=store_path)

    store.append_snapshot(
        (
            RankObservation(
                symbol="ABC",
                as_of="2026-08-17",
                rank=260,
                ranked_universe_size=500,
                universe_source="TEST",
                profile_name="DEFAULT",
            ),
            RankObservation(
                symbol="ABC",
                as_of="2026-08-19",
                rank=80,
                ranked_universe_size=500,
                universe_source="TEST",
                profile_name="DEFAULT",
            ),
        )
    )

    result = build_current_visibility_context(store=store)

    assert len(result) == 1
    assert result[0].symbol == "ABC"
    assert result[0].current_rank == 80
    assert result[0].visibility_state == "IMPROVING"
