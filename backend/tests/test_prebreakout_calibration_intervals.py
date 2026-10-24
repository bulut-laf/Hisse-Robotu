import pytest

from backend.app.prebreakout.prebreakout_calibration import (
    PreBreakoutCalibrationRow,
    _wilson_interval,
    asama_guven_araliklarini_hesapla,
    asama_guven_araliklarini_tabloya_cevir,
    temkinli_lider_asamayi_sec,
)


def row(stage: str, measured: int, successful: int) -> PreBreakoutCalibrationRow:
    return PreBreakoutCalibrationRow(
        stage=stage,
        candidate_count=measured,
        measured_count=measured,
        successful_count=successful,
        limited_count=0,
        false_positive_count=measured-successful,
        success_rate_pct=round(successful / measured * 100, 2) if measured else 0.0,
        average_close_return_5d_pct=None,
        average_close_return_10d_pct=None,
        average_close_return_20d_pct=None,
        average_max_return_5d_pct=None,
        average_max_return_10d_pct=None,
        average_max_return_20d_pct=None,
        average_min_return_5d_pct=None,
        average_min_return_10d_pct=None,
        average_min_return_20d_pct=None,
    )


def test_wilson_araligi_bos_orneklemde_sifirdir() -> None:
    assert _wilson_interval(0, 0) == (0.0, 0.0)


def test_wilson_araligi_gecersiz_sayilari_reddeder() -> None:
    with pytest.raises(ValueError):
        _wilson_interval(4, 3)


def test_guven_araligi_yuzde_sinirlarinda_kalir() -> None:
    result = asama_guven_araliklarini_hesapla((row("E3", 10, 6),))[0]
    assert 0.0 <= result.confidence_low_pct <= 60.0
    assert 60.0 <= result.confidence_high_pct <= 100.0


def test_yetersiz_ornekleme_temkinli_sira_verilmez() -> None:
    result = asama_guven_araliklarini_hesapla(
        (row("E4", 2, 2),), minimum_sample_size=3
    )[0]
    assert result.sample_sufficient is False
    assert result.conservative_rank is None


def test_temkinli_sira_sadece_ham_basari_oranina_bakmaz() -> None:
    results = asama_guven_araliklarini_hesapla(
        (row("E2", 3, 3), row("E3", 20, 14)), minimum_sample_size=3
    )
    leader = temkinli_lider_asamayi_sec(results)
    assert leader is not None
    assert leader.stage == "E3"


def test_esit_alt_sinirda_daha_yuksek_basarili_oran_onceliklidir() -> None:
    results = asama_guven_araliklarini_hesapla(
        (row("E2", 10, 5), row("E3", 10, 5)), minimum_sample_size=3
    )
    assert sorted(item.conservative_rank for item in results) == [1, 2]


def test_temkinli_lider_yoksa_none_doner() -> None:
    results = asama_guven_araliklarini_hesapla(
        (row("E1", 1, 1),), minimum_sample_size=3
    )
    assert temkinli_lider_asamayi_sec(results) is None


def test_guven_araligi_tablosu_karar_sutunlarini_icerir() -> None:
    rows = asama_guven_araliklarini_hesapla((row("E3", 10, 6),))
    table = asama_guven_araliklarini_tabloya_cevir(rows)
    assert "%95 alt sınır" in table.columns
    assert "Temkinli sıra" in table.columns
    assert table.iloc[0]["Örneklem yeterli"] == "Evet"
