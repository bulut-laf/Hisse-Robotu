from pathlib import Path

from backend.app.analysis.ranking_memory import (
    RankObservationJsonlStore,
    observations_from_research_rows,
    rank_history_for_symbol,
)


def test_observations_capture_existing_research_rank_without_rescoring():
    rows = (
        {"Hisse": "AAA", "Sıra": 1},
        {"Hisse": "BBB.IS", "Sıra": 2},
        {"Hisse": "CCC", "Sıra": 3},
    )
    items = observations_from_research_rows(
        rows=rows,
        as_of="2026-08-18",
        universe_source="BIST",
        profile_name="default",
    )
    assert [item.symbol for item in items] == ["AAA", "BBB", "CCC"]
    assert [item.rank for item in items] == [1, 2, 3]
    assert all(item.ranked_universe_size == 3 for item in items)


def test_append_snapshot_is_idempotent_for_same_session(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank.jsonl")
    items = observations_from_research_rows(
        rows=({"Hisse": "AAA", "Sıra": 7},),
        as_of="2026-08-18",
        universe_source="BIST",
        profile_name="default",
    )
    assert store.append_snapshot(items) == 1
    assert store.append_snapshot(items) == 0
    assert len(store.list()) == 1


def test_rank_history_for_symbol_orders_sessions(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank.jsonl")
    newer = observations_from_research_rows(
        rows=({"Hisse": "AAA", "Sıra": 120},),
        as_of="2026-08-18",
        universe_source="BIST",
        profile_name="default",
    )
    older = observations_from_research_rows(
        rows=({"Hisse": "AAA", "Sıra": 400},),
        as_of="2026-08-15",
        universe_source="BIST",
        profile_name="default",
    )
    store.append_snapshot(newer)
    store.append_snapshot(older)
    history = rank_history_for_symbol(store.list(), "AAA")
    assert [(item.as_of, item.rank) for item in history] == [
        ("2026-08-15", 400),
        ("2026-08-18", 120),
    ]


def test_dashboard_observes_full_research_rows_before_visible_filter():
    root = Path(__file__).resolve().parents[2]
    text = (root / "backend" / "dashboard.py").read_text(encoding="utf-8")
    marker = "RANKING_JUMP_V1_BLOCK1"
    assert marker in text
    observation = text.index("observations_from_research_rows(")
    filtered = text.index("kayitlar = [", observation)
    assert observation < filtered
    assert "rows=_three_all_rows" in text
    assert "ranked_universe_size" not in text[observation:filtered]
