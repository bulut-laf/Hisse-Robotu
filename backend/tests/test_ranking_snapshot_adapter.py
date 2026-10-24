from backend.app.analysis.ranking_snapshot_adapter import (
    persist_research_rank_snapshot,
)
from backend.app.analysis.ranking_memory import RankObservationJsonlStore


def test_snapshot_adapter_persists(tmp_path):

    store = RankObservationJsonlStore(
        path=tmp_path / "rank_observations.jsonl"
    )

    rows = (
        {
            "Hisse": "ABC",
            "Sıra": 10,
        },
        {
            "Hisse": "XYZ",
            "Sıra": 20,
        },
    )

    count = persist_research_rank_snapshot(
        rows=rows,
        as_of="2026-08-19",
        universe_source="TEST",
        profile_name="DEFAULT",
        store=store,
    )

    assert count == 2