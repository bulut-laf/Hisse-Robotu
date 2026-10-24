from datetime import date

import pytest

from backend.app.prebreakout.prebreakout_historical_validation import (
    HistoricalCandidateObservation,
    build_historical_validation_report,
    captured_move_ratio_pct,
    first_appearance_records,
    forward_return_pct,
    momentum_band_label,
    rank_band_label,
)


def obs(day, symbol, rank, stage, momentum, upside, adverse, price=100):
    return HistoricalCandidateObservation(
        cut_date=date(2026, 7, day),
        symbol=symbol,
        rank=rank,
        stage=stage,
        momentum=momentum,
        signal_price=price,
        future_max_upside_pct=upside,
        max_adverse_excursion_pct=adverse,
    )


def test_rank_bantlari():
    assert rank_band_label(1) == "1-10"
    assert rank_band_label(10) == "1-10"
    assert rank_band_label(11) == "11-20"
    assert rank_band_label(20) == "11-20"
    assert rank_band_label(21) == "21-30"
    assert rank_band_label(30) == "21-30"
    assert rank_band_label(31) == "31+"
    assert rank_band_label(None) == "İzleme dışı"


def test_momentum_bantlari():
    assert momentum_band_label(44.9) == "<45"
    assert momentum_band_label(45) == "45-54"
    assert momentum_band_label(55) == "55-64"
    assert momentum_band_label(65) == "65-74"
    assert momentum_band_label(75) == "75+"
    assert momentum_band_label(None) == "Momentum yok"


def test_rank_bandi_hit_rate_hesabi():
    rows = (
        obs(1, "AAA", 12, "E1", 60, 15, 3),
        obs(1, "BBB", 18, "E2", 63, 5, 4),
        obs(1, "CCC", 25, "E0", 52, 20, 6),
    )
    report = build_historical_validation_report(rows, success_threshold_pct=10)
    b1120 = next(x for x in report.rank_bands if x.label == "11-20")
    assert b1120.observations == 2
    assert b1120.success_count == 1
    assert b1120.hit_rate_pct == pytest.approx(50.0)


def test_stage_istatistikleri():
    rows = (
        obs(1, "AAA", 12, "E1", 60, 15, 3),
        obs(2, "BBB", 14, "E1", 62, 12, 5),
        obs(3, "CCC", 5, "B", 80, 2, 8),
    )
    report = build_historical_validation_report(rows)
    e1 = next(x for x in report.stage_stats if x.label == "E1")
    assert e1.observations == 2
    assert e1.success_count == 2
    assert e1.hit_rate_pct == pytest.approx(100.0)


def test_momentum_istatistikleri():
    rows = (
        obs(1, "AAA", 12, "E1", 60, 15, 3),
        obs(2, "BBB", 20, "E2", 63, 12, 5),
        obs(3, "CCC", 5, "B", 80, 2, 8),
    )
    report = build_historical_validation_report(rows)
    m5564 = next(x for x in report.momentum_bands if x.label == "55-64")
    assert m5564.observations == 2
    assert m5564.hit_rate_pct == pytest.approx(100.0)


def test_olculemeyen_ileri_getiri_hit_rate_disinda_kalir():
    rows = (
        obs(1, "AAA", 12, "E1", 60, None, 3),
        obs(2, "BBB", 18, "E1", 61, 12, 4),
    )
    report = build_historical_validation_report(rows)
    b = next(x for x in report.rank_bands if x.label == "11-20")
    assert b.observations == 2
    assert b.success_count == 1
    assert b.hit_rate_pct == pytest.approx(100.0)


def test_ilk_gorunme_tek_hisseyi_bir_kez_sayar():
    rows = (
        obs(5, "TRMET", 25, "E0", 50, 18, 4),
        obs(6, "TRMET", 18, "E1", 58, 14, 5),
        obs(7, "TRMET", 5, "B", 80, 3, 9),
    )
    first = first_appearance_records(rows)
    assert len(first) == 1
    assert first[0].first_cut_date == date(2026, 7, 5)
    assert first[0].first_rank == 25
    assert first[0].best_future_upside_pct == pytest.approx(18.0)


def test_rapor_raw_ve_unique_symbol_sayisini_ayirir():
    rows = (
        obs(1, "AAA", 20, "E1", 60, 15, 3),
        obs(2, "AAA", 10, "E2", 70, 9, 4),
        obs(1, "BBB", 22, "E0", 55, 11, 5),
    )
    report = build_historical_validation_report(rows)
    assert report.total_observations == 3
    assert report.unique_symbols == 2
    assert len(report.first_appearances) == 2


def test_yakalanan_hareket_orani():
    # 100 -> 130 toplam hareket. 120 seviyesinde ilk 5'e girerse
    # hareketin 20/30'u, yani %66.67'si zaten gerçekleşmiştir.
    ratio = captured_move_ratio_pct(
        move_start_price=100,
        rank_entry_price=120,
        peak_price=130,
    )
    assert ratio == pytest.approx(66.6666667)


def test_hareket_yoksa_yakalanan_oran_none():
    assert captured_move_ratio_pct(
        move_start_price=100,
        rank_entry_price=100,
        peak_price=100,
    ) is None


def test_ileri_getiri():
    assert forward_return_pct(100, 110) == pytest.approx(10.0)


def test_esik_pozitif_olmali():
    with pytest.raises(ValueError):
        build_historical_validation_report((), success_threshold_pct=0)


def test_gecersiz_rank_reddedilir():
    with pytest.raises(ValueError):
        obs(1, "AAA", 0, "E0", 50, 10, 2)


def test_gecersiz_fiyat_reddedilir():
    with pytest.raises(ValueError):
        HistoricalCandidateObservation(
            cut_date=date(2026, 7, 1),
            symbol="AAA",
            rank=10,
            stage="E1",
            momentum=60,
            signal_price=0,
            future_max_upside_pct=10,
            max_adverse_excursion_pct=2,
        )


def test_bos_symbol_reddedilir():
    with pytest.raises(ValueError):
        HistoricalCandidateObservation(
            cut_date=date(2026, 7, 1),
            symbol=" ",
            rank=10,
            stage="E1",
            momentum=60,
            signal_price=100,
            future_max_upside_pct=10,
            max_adverse_excursion_pct=2,
        )
