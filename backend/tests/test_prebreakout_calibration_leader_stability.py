from backend.app.prebreakout.prebreakout_calibration import (
    PreBreakoutCalibrationRow,
    lider_duyarlilik_senaryolarini_hesapla,
    lider_duyarlilik_senaryolarini_tabloya_cevir,
    lider_kararlilik_ozetini_hesapla,
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


def test_kararli_lider_tek_gozlem_senaryolarinda_korunur() -> None:
    rows = (row("E2", 12, 5), row("E3", 20, 16))
    summary = lider_kararlilik_ozetini_hesapla(rows, minimum_sample_size=3)
    assert summary.baseline_leader == "E3"
    assert summary.scenario_count == 4
    assert summary.retention_rate_pct >= 80.0
    assert summary.stable is True


def test_kucuk_orneklemli_lider_kirilgan_olabilir() -> None:
    rows = (row("E2", 3, 3), row("E3", 10, 7))
    summary = lider_kararlilik_ozetini_hesapla(rows, minimum_sample_size=3)
    assert summary.baseline_leader == "E2"
    assert summary.scenario_count == 3
    assert summary.stable is False
    assert "kırılgan" in summary.note


def test_lider_yoksa_kararlilik_olculemez() -> None:
    summary = lider_kararlilik_ozetini_hesapla(
        (row("E1", 2, 2),), minimum_sample_size=3
    )
    assert summary.baseline_leader is None
    assert summary.stable is False
    assert "ölçülemedi" in summary.note


def test_duyarlilik_senaryolari_basarili_ve_basarisiz_gozlemi_ayirir() -> None:
    scenarios = lider_duyarlilik_senaryolarini_hesapla(
        (row("E2", 5, 3), row("E3", 6, 4)), minimum_sample_size=3
    )
    assert len(scenarios) == 4
    assert {item.removed_outcome for item in scenarios} == {
        "Başarılı gözlem",
        "Başarılı olmayan gözlem",
    }


def test_duyarlilik_tablosu_karar_sutunlarini_icerir() -> None:
    scenarios = lider_duyarlilik_senaryolarini_hesapla(
        (row("E2", 5, 3), row("E3", 6, 4)), minimum_sample_size=3
    )
    table = lider_duyarlilik_senaryolarini_tabloya_cevir(scenarios)
    assert "Senaryo lideri" in table.columns
    assert "Mevcut lider korundu" in table.columns
