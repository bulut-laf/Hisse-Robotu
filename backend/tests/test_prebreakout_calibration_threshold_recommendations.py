import pytest

from backend.app.prebreakout.prebreakout_calibration import (
    PreBreakoutCalibrationRow,
    PreBreakoutMomentumCalibrationRow,
    kalibrasyon_esik_onerilerini_hesapla,
    kalibrasyon_esik_onerilerini_tabloya_cevir,
)


def stage_row(stage: str, measured: int, successful: int) -> PreBreakoutCalibrationRow:
    return PreBreakoutCalibrationRow(
        stage=stage,
        candidate_count=measured,
        measured_count=measured,
        successful_count=successful,
        limited_count=0,
        false_positive_count=measured - successful,
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


def momentum_row(stage: str, band: str, measured: int, successful: int) -> PreBreakoutMomentumCalibrationRow:
    return PreBreakoutMomentumCalibrationRow(
        stage=stage,
        momentum_band=band,
        candidate_count=measured,
        measured_count=measured,
        successful_count=successful,
        success_rate_pct=round(successful / measured * 100, 2) if measured else 0.0,
        average_macd_histogram_slope=None,
        average_rsi_slope=None,
    )


def test_kararli_temkinli_lider_kontrollu_dogrulama_adayi_olur() -> None:
    recommendations = kalibrasyon_esik_onerilerini_hesapla(
        (stage_row("E2", 12, 5), stage_row("E3", 20, 16)),
        (
            momentum_row("E2", "10-14", 12, 5),
            momentum_row("E3", "10-14", 8, 5),
            momentum_row("E3", "15-20", 12, 11),
        ),
        minimum_sample_size=3,
    )
    e3 = next(item for item in recommendations if item.stage == "E3")
    assert e3.recommended_action == "Kontrollü doğrulama adayı"
    assert e3.recommended_minimum_momentum_score == 15
    assert e3.leader_stable is True
    assert e3.auto_apply is False


def test_yetersiz_orneklem_esik_onerisi_uretmez() -> None:
    recommendations = kalibrasyon_esik_onerilerini_hesapla(
        (stage_row("E2", 2, 2),),
        (momentum_row("E2", "15-20", 2, 2),),
        minimum_sample_size=3,
    )
    assert recommendations[0].recommended_action == "Veri biriktir"
    assert recommendations[0].recommended_minimum_momentum_score is None
    assert recommendations[0].evidence_level == "Yetersiz"


def test_zayif_alt_guven_siniri_gevsetme_onermez() -> None:
    recommendations = kalibrasyon_esik_onerilerini_hesapla(
        (stage_row("E1", 10, 1),),
        (momentum_row("E1", "0-9", 10, 1),),
        minimum_sample_size=3,
        minimum_confidence_low_pct=20.0,
    )
    assert recommendations[0].recommended_action == "Gevşetme önerilmez"


def test_esik_onerileri_uretim_motoruna_otomatik_uygulanmaz() -> None:
    recommendations = kalibrasyon_esik_onerilerini_hesapla(
        (stage_row("E3", 20, 16),),
        (momentum_row("E3", "15-20", 20, 16),),
    )
    assert all(item.auto_apply is False for item in recommendations)


def test_esik_onerisi_parametre_dogrulamasi() -> None:
    with pytest.raises(ValueError):
        kalibrasyon_esik_onerilerini_hesapla((), (), minimum_sample_size=0)
    with pytest.raises(ValueError):
        kalibrasyon_esik_onerilerini_hesapla(
            (), (), minimum_confidence_low_pct=101.0
        )


def test_esik_onerisi_tablosu_karar_sutunlarini_icerir() -> None:
    recommendations = kalibrasyon_esik_onerilerini_hesapla(
        (stage_row("E3", 20, 16),),
        (momentum_row("E3", "15-20", 20, 16),),
    )
    table = kalibrasyon_esik_onerilerini_tabloya_cevir(recommendations)
    assert "Önerilen minimum momentum" in table.columns
    assert "Otomatik uygulanır" in table.columns
    assert set(table["Otomatik uygulanır"]) == {"Hayır"}
