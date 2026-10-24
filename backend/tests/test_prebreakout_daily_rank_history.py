from datetime import date

import pytest

from backend.app.prebreakout.prebreakout_daily_rank_history import (
    DailyRankObservation,
    build_all_journeys,
    build_symbol_journey,
    summarize_journeys,
)


def o(day, rank, score, momentum, stage, price=None, peak=None):
    return DailyRankObservation(
        cut_date=date(2026, 7, day),
        symbol="TRMET",
        rank=rank,
        score=score,
        momentum=momentum,
        stage=stage,
        signal_price=price,
        future_peak_price=peak,
        future_peak_date=date(2026, 7, 15) if peak else None,
    )


def test_sira_ivmesi_yukari_pozitif():
    j = build_symbol_journey((o(1, 30, 50, 45, "E0"), o(2, 24, 56, 50, "E1")))
    assert j.points[-1].rank_velocity == pytest.approx(6.0)


def test_skor_ve_momentum_ivmesi():
    j = build_symbol_journey((o(1, 30, 50, 45, "E0"), o(2, 24, 56, 50, "E1")))
    assert j.points[-1].score_velocity == pytest.approx(6.0)
    assert j.points[-1].momentum_velocity == pytest.approx(5.0)


def test_erken_radar_ilk_tetik():
    j = build_symbol_journey((
        o(1, 34, 50, 45, "E0"), o(2, 28, 56, 50, "E1"),
        o(3, 22, 63, 55, "E2"), o(4, 9, 72, 61, "B"), o(5, 4, 85, 67, "B"),
    ))
    assert j.first_early_radar_date == date(2026, 7, 2)
    assert j.first_early_radar_rank == 28


def test_ilk_bant_tarihleri():
    j = build_symbol_journey((
        o(1, 35, 50, 45, "E0"), o(2, 28, 56, 50, "E1"),
        o(3, 19, 63, 55, "E2"), o(4, 9, 72, 61, "B"), o(5, 4, 85, 67, "B"),
    ))
    assert j.first_top30_date == date(2026, 7, 2)
    assert j.first_top20_date == date(2026, 7, 3)
    assert j.first_top10_date == date(2026, 7, 4)
    assert j.first_top5_date == date(2026, 7, 5)


def test_radar_top5_arasi_seans():
    j = build_symbol_journey((
        o(1, 34, 50, 45, "E0"), o(2, 28, 56, 50, "E1"),
        o(3, 22, 63, 55, "E2"), o(4, 9, 72, 61, "B"), o(5, 4, 85, 67, "B"),
    ))
    assert j.sessions_radar_to_top5 == 3


def test_ilk5e_gelene_kadar_hareketin_ne_kadari_gerceklesmis():
    j = build_symbol_journey((
        o(1, 30, 50, 45, "E0", price=100, peak=130),
        o(2, 20, 60, 52, "E1", price=108),
        o(3, 10, 70, 60, "E2", price=116),
        o(4, 5, 85, 68, "B", price=124),
    ))
    assert j.move_captured_before_top5_pct == pytest.approx(80.0)


def test_erken_radar_yoksa_none():
    j = build_symbol_journey((o(1, 25, 50, 45, "D"), o(2, 20, 48, 44, "D")))
    assert j.first_early_radar_date is None


def test_build_all_journeys():
    rows = [
        DailyRankObservation(date(2026, 7, 1), "BBB", 20, 60, 55, "E1"),
        DailyRankObservation(date(2026, 7, 1), "AAA", 22, 58, 52, "E0"),
        DailyRankObservation(date(2026, 7, 2), "AAA", 18, 62, 56, "E1"),
    ]
    journeys = build_all_journeys(rows)
    assert [x.symbol for x in journeys] == ["AAA", "BBB"]


def test_summary():
    j1 = build_symbol_journey((
        DailyRankObservation(date(2026, 7, 1), "AAA", 28, 55, 50, "E1"),
        DailyRankObservation(date(2026, 7, 2), "AAA", 20, 60, 55, "E2"),
        DailyRankObservation(date(2026, 7, 3), "AAA", 5, 80, 65, "B"),
    ))
    j2 = build_symbol_journey((
        DailyRankObservation(date(2026, 7, 1), "BBB", 40, 40, 35, "E0"),
        DailyRankObservation(date(2026, 7, 2), "BBB", 35, 42, 36, "E0"),
    ))
    s = summarize_journeys((j1, j2))
    assert s.symbols == 2
    assert s.radar_triggered == 1
    assert s.reached_top5 == 1
    assert s.radar_before_top5 == 1
    assert s.avg_sessions_radar_to_top5 == pytest.approx(1.0)


def test_tek_hisse_zorunlu():
    with pytest.raises(ValueError):
        build_symbol_journey((
            DailyRankObservation(date(2026, 7, 1), "AAA", 20, 50, 45, "E1"),
            DailyRankObservation(date(2026, 7, 2), "BBB", 18, 55, 50, "E1"),
        ))


def test_bos_girdi_reddedilir():
    with pytest.raises(ValueError):
        build_symbol_journey(())


def test_gecersiz_rank():
    with pytest.raises(ValueError):
        DailyRankObservation(date(2026, 7, 1), "AAA", 0, 50, 45, "E1")


def test_gecersiz_score():
    with pytest.raises(ValueError):
        DailyRankObservation(date(2026, 7, 1), "AAA", 10, 101, 45, "E1")


def test_gecersiz_signal_price():
    with pytest.raises(ValueError):
        DailyRankObservation(date(2026, 7, 1), "AAA", 10, 50, 45, "E1", signal_price=0)


def test_gecersiz_peak_price():
    with pytest.raises(ValueError):
        DailyRankObservation(date(2026, 7, 1), "AAA", 10, 50, 45, "E1", future_peak_price=0)
