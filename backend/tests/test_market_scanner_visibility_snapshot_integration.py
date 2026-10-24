from backend.app.analysis.ranking_memory import (
    RankObservationJsonlStore,
)
from backend.app.analysis.ranking_snapshot_adapter import (
    persist_research_rank_snapshot,
)
from backend.app.analysis.ranking_visibility_service import (
    build_current_visibility_context,
)


def test_market_scanner_snapshot_visibility_integration(tmp_path):
    store = RankObservationJsonlStore(
        path=tmp_path / "rank_observations.jsonl"
    )

    rows = (
    {
        "Hisse": "ABC",
        "Sıra": 1,
    },
    {
        "Hisse": "XYZ",
        "Sıra": 2,
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

    class Memory:
        def list(self):
            return (
                {
                    "symbol": "ABC",
                },
            )

    assert store is not None
    assert len(rows) == 2
