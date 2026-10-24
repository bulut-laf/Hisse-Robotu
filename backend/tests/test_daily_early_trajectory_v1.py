from pathlib import Path

from backend.app.analysis.daily_early_trajectory import (
    build_daily_early_trajectory_candidates,
    daily_early_trajectory_rows,
)
from backend.app.analysis.ranking_trajectory import RankTrajectory


def traj(
    symbol: str,
    *,
    current: int,
    r1: int,
    r3: int,
    r5: int,
    comparable: bool = True,
) -> RankTrajectory:
    return RankTrajectory(
        symbol=symbol,
        as_of="2026-08-25",
        current_rank=current,
        current_universe_size=548,
        rank_1s=r1,
        rank_3s=r3,
        rank_5s=r5,
        week_start_rank=r5,
        gain_1s=r1 - current,
        gain_3s=r3 - current,
        gain_5s=r5 - current,
        normalized_current=current / 548,
        normalized_3s=r3 / 548,
        normalized_gain_3s=(r3 - current) / 548,
        lifecycle="IVMELENIYOR",
        zone_events=(),
        comparable=comparable,
    )


def test_healthy_path_is_selected_and_sorted_by_3s_then_5s_then_1s():
    rows = (
        traj("AAA", current=26, r1=41, r3=68, r5=96),  # +15 / +42 / +70
        traj("BBB", current=29, r1=39, r3=59, r5=90),  # +10 / +30 / +61
        traj("CCC", current=24, r1=31, r3=54, r5=80),  # +7 / +30 / +56
    )
    result = build_daily_early_trajectory_candidates(rows)
    assert [item.symbol for item in result] == ["AAA", "BBB", "CCC"]
    assert result[0].rank_path == "96 → 68 → 41 → 26"
    assert (result[0].gain_1s, result[0].gain_3s, result[0].gain_5s) == (
        15,
        42,
        70,
    )


def test_zigzag_primary_duplicate_out_of_band_and_noncomparable_are_excluded():
    rows = (
        traj("GOOD", current=30, r1=45, r3=70, r5=100),
        traj("ZIG", current=26, r1=55, r3=41, r5=96),
        traj("PRIMARY", current=27, r1=40, r3=60, r5=90),
        traj("TOP", current=15, r1=30, r3=50, r5=75),
        traj("BLOCK", current=28, r1=45, r3=65, r5=95, comparable=False),
    )
    result = build_daily_early_trajectory_candidates(
        rows,
        primary_symbols=("PRIMARY",),
    )
    assert [item.symbol for item in result] == ["GOOD"]


def test_rows_show_exact_rank_path_and_gains():
    item = build_daily_early_trajectory_candidates(
        (traj("AAA", current=26, r1=41, r3=68, r5=96),)
    )[0]
    row = daily_early_trajectory_rows((item,))[0]
    assert row["Öncelik"] == 6
    assert row["Sıra yolu"] == "96 → 68 → 41 → 26"
    assert row["1S Δ"] == "+15"
    assert row["3S Δ"] == "+42"
    assert row["5S Δ"] == "+70"
    assert row["Hareket"] == "SAĞLIKLI İVMELENME"


def test_dashboard_keeps_primary_five_decision_authority_and_adds_early_five():
    source = Path("backend/dashboard.py").read_text(encoding="utf-8")
    assert "DAILY_10_TRAJECTORY_V1" in source
    assert 'st.markdown("#### Bugünün 10 Araştırma Adayı")' in source
    assert 'st.markdown("#### Bugünün 5 Adayı")' in source
    assert "limit=5," in source
    assert "build_daily_buy_decisions(" in source
    assert "Erken 5 — sağlıklı sıra göçü" in source
    assert "daily_early_trajectory_rows" in source
    assert "yeni teknik skor, işlem sinyali veya AL/SAT kararı üretmez" in source