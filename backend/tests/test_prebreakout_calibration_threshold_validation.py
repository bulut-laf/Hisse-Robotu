import pytest

from backend.app.prebreakout.prebreakout_calibration import (
    PreBreakoutMomentumCalibrationRow,
    PreBreakoutThresholdRecommendation,
    esik_dogrulamalarini_tabloya_cevir,
    esik_onerilerini_tarihsel_dogrula,
)


def momentum(band: str, measured: int, successful: int):
    return PreBreakoutMomentumCalibrationRow(
        stage="E3", momentum_band=band, candidate_count=measured,
        measured_count=measured, successful_count=successful,
        success_rate_pct=round(successful / measured * 100, 2),
        average_macd_histogram_slope=None, average_rsi_slope=None,
    )


def recommendation(action="Kontrollü doğrulama adayı", score=15):
    return PreBreakoutThresholdRecommendation(
        stage="E3", recommended_action=action,
        recommended_minimum_momentum_score=score, evidence_level="Güçlü",
        confidence_low_pct=40.0, measured_count=20, leader_stable=True,
        auto_apply=False, rationale="test",
    )


def test_onerilen_esik_mevcut_esikle_ayni_orneklemde_karsilastirilir():
    rows = esik_onerilerini_tarihsel_dogrula(
        (recommendation(),), (momentum("10-14", 8, 4), momentum("15-20", 12, 10))
    )
    item = rows[0]
    assert item.baseline_measured_count == 20
    assert item.candidate_measured_count == 12
    assert item.candidate_success_rate_pct > item.baseline_success_rate_pct
    assert item.verdict == "Kontrollü uygulama adayı"
    assert item.auto_apply is False


def test_asiri_orneklem_kaybi_adayi_reddeder():
    rows = esik_onerilerini_tarihsel_dogrula(
        (recommendation(),), (momentum("10-14", 18, 8), momentum("15-20", 2, 2)),
        minimum_candidate_sample_size=2,
    )
    assert rows[0].verdict == "Aşırı örneklem kaybı"


def test_yetersiz_aday_orneklemi_uygulanmaz():
    rows = esik_onerilerini_tarihsel_dogrula(
        (recommendation(),), (momentum("10-14", 8, 4), momentum("15-20", 2, 2))
    )
    assert rows[0].verdict == "Örneklem yetersiz"


def test_kontrollu_dogrulama_adayi_olmayan_oneri_atlanir():
    rows = esik_onerilerini_tarihsel_dogrula(
        (recommendation(action="Mevcut eşiği koru"),), (momentum("15-20", 10, 8),)
    )
    assert rows == ()


def test_parametre_dogrulamasi():
    with pytest.raises(ValueError):
        esik_onerilerini_tarihsel_dogrula((), (), minimum_candidate_sample_size=0)
    with pytest.raises(ValueError):
        esik_onerilerini_tarihsel_dogrula((), (), minimum_sample_retention_pct=101)


def test_dogrulama_tablosu_karar_ve_guven_sutunlarini_icerir():
    rows = esik_onerilerini_tarihsel_dogrula(
        (recommendation(),), (momentum("10-14", 8, 4), momentum("15-20", 12, 10))
    )
    table = esik_dogrulamalarini_tabloya_cevir(rows)
    assert "Örneklem korunma %" in table.columns
    assert "Öneri %95 alt sınır" in table.columns
    assert set(table["Otomatik uygulanır"]) == {"Hayır"}
