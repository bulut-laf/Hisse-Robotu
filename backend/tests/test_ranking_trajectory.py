from backend.app.analysis.ranking_memory import RankObservation
from backend.app.analysis.ranking_trajectory import (
    build_rank_trajectory,
    build_rank_trajectories,
)


def obs(day, rank, size=500, symbol="AAA", source="BIST", profile="default"):
    return RankObservation(
        as_of=day,
        symbol=symbol,
        rank=rank,
        ranked_universe_size=size,
        universe_source=source,
        profile_name=profile,
    )


def test_three_session_gain_and_normalized_movement():
    items = (
        obs("2026-08-13", 487),
        obs("2026-08-14", 311),
        obs("2026-08-17", 146),
        obs("2026-08-18", 62),
    )
    t = build_rank_trajectory(items, "AAA")
    assert t is not None
    assert t.current_rank == 62
    assert t.rank_3s == 487
    assert t.gain_3s == 425
    assert round(t.normalized_current, 3) == round(62 / 500, 3)
    assert round(t.normalized_gain_3s, 3) == round((487 - 62) / 500, 3)
    assert t.lifecycle in {"IVMELENIYOR", "UST_BOLGEYE_YERLESIYOR"}


def test_zone_transition_detects_new_top100():
    items = (
        obs("2026-08-13", 180),
        obs("2026-08-14", 150),
        obs("2026-08-17", 120),
        obs("2026-08-18", 80),
    )
    t = build_rank_trajectory(items, "AAA")
    assert "YENI_TOP100" in t.zone_events


def test_universe_size_changes_use_normalized_positions():
    items = (
        obs("2026-08-13", 400, 600),
        obs("2026-08-14", 300, 580),
        obs("2026-08-17", 200, 560),
        obs("2026-08-18", 100, 540),
    )
    t = build_rank_trajectory(items, "AAA")
    assert t.gain_3s == 300
    assert t.normalized_gain_3s is not None
    assert t.normalized_gain_3s > 0
    assert t.comparable is True


def test_source_or_profile_change_marks_not_comparable():
    items = (
        obs("2026-08-13", 300, source="OLD"),
        obs("2026-08-14", 250),
        obs("2026-08-17", 200),
        obs("2026-08-18", 100),
    )
    t = build_rank_trajectory(items, "AAA")
    assert t.comparable is False


def test_failed_jump_and_fade_are_separate_from_acceleration():
    failed = (
        obs("2026-08-13", 480),
        obs("2026-08-14", 170),
        obs("2026-08-17", 155),
        obs("2026-08-18", 500),
    )
    t = build_rank_trajectory(failed, "AAA")
    assert t.lifecycle == "SICRAMA_BASARISIZ"


def test_collection_sorted_by_three_session_gain():
    items = (
        obs("2026-08-13", 480, symbol="AAA"),
        obs("2026-08-14", 300, symbol="AAA"),
        obs("2026-08-17", 200, symbol="AAA"),
        obs("2026-08-18", 100, symbol="AAA"),
        obs("2026-08-13", 220, symbol="BBB"),
        obs("2026-08-14", 180, symbol="BBB"),
        obs("2026-08-17", 160, symbol="BBB"),
        obs("2026-08-18", 140, symbol="BBB"),
    )
    rows = build_rank_trajectories(items)
    assert [item.symbol for item in rows] == ["AAA", "BBB"]
    assert rows[0].gain_3s == 380
