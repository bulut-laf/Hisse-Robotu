from backend.app.analysis.ranking_memory import RankObservation
from backend.app.analysis.ranking_trajectory import build_rank_trajectory


def obs(day, rank):
    return RankObservation(
        as_of=day,
        symbol="AAA",
        rank=rank,
        ranked_universe_size=100,
        universe_source="BIST",
        profile_name="Dengeli",
    )


def test_ddmmyyyy_research_dates_are_supported():
    items = (
        obs("13/08/2026", 90),
        obs("14/08/2026", 70),
        obs("17/08/2026", 50),
        obs("18/08/2026", 30),
    )
    result = build_rank_trajectory(items, "AAA")
    assert result is not None
    assert result.current_rank == 30
    assert result.rank_3s == 90
    assert result.gain_3s == 60


def test_iso_dates_remain_supported():
    items = (
        obs("2026-08-13", 90),
        obs("2026-08-14", 70),
        obs("2026-08-17", 50),
        obs("2026-08-18", 30),
    )
    result = build_rank_trajectory(items, "AAA")
    assert result is not None
    assert result.current_rank == 30
