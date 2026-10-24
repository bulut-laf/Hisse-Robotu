from pathlib import Path

from backend.app.prebreakout.prebreakout_v2_decision_history import (
    DecisionHistoryRecord,
    PeriodComparison,
    donemi_ozetle,
    donem_karsilastirma_raporunu_metne_cevir,
    karar_gecmisine_ekle,
    karar_gecmisini_yukle,
    kullanim_donemlerini_karsilastir,
)


def _r(period, day, decision, success, false_pos, portfolio):
    return DecisionHistoryRecord(
        period_id=period,
        recorded_on=f"2026-08-{day:02d}",
        observation_day=day,
        decision=decision,
        success_rate_pct=success,
        false_positive_rate_pct=false_pos,
        portfolio_return_pct=portfolio,
    )


def test_append_only_ve_duplicate_koruma(tmp_path: Path):
    path = tmp_path / "history.jsonl"
    record = _r("P1", 1, "Modeli koru", 50, 30, 2)
    assert karar_gecmisine_ekle(path, record) is True
    assert karar_gecmisine_ekle(path, record) is False
    assert len(karar_gecmisini_yukle(path)) == 1


def test_donem_ozeti_baskin_karari_hesaplar():
    records = [
        _r("P1", 1, "Modeli koru", 50, 30, 2),
        _r("P1", 2, "Modeli koru", 52, 28, 3),
        _r("P1", 3, "İncele", 48, 35, 1),
    ]
    summary = donemi_ozetle(records, "P1")
    assert summary.record_count == 3
    assert summary.dominant_decision == "Modeli koru"
    assert summary.model_keep_share == 0.6667


def test_yetersiz_donem_verisi():
    report = kullanim_donemlerini_karsilastir(
        [_r("P2", 1, "Modeli koru", 50, 30, 2)],
        current_period="P2",
        previous_period="P1",
    )
    assert report.comparison is PeriodComparison.YETERSIZ_VERI


def test_iyilesen_donem():
    records = [
        _r("P1", 1, "İncele", 40, 50, -1),
        _r("P1", 2, "Kalibrasyon adayı", 42, 52, -2),
        _r("P1", 3, "İncele", 41, 49, -1),
        _r("P2", 4, "Modeli koru", 55, 35, 3),
        _r("P2", 5, "Modeli koru", 56, 34, 4),
        _r("P2", 6, "Modeli koru", 54, 33, 3),
    ]
    report = kullanim_donemlerini_karsilastir(
        records, current_period="P2", previous_period="P1"
    )
    assert report.comparison is PeriodComparison.IYILESIYOR


def test_kotulesen_donem():
    records = [
        _r("P1", 1, "Modeli koru", 55, 30, 4),
        _r("P1", 2, "Modeli koru", 57, 28, 5),
        _r("P1", 3, "Modeli koru", 56, 29, 4),
        _r("P2", 4, "Kalibrasyon adayı", 40, 50, -2),
        _r("P2", 5, "Kalibrasyon adayı", 39, 52, -3),
        _r("P2", 6, "İncele", 41, 49, -2),
    ]
    report = kullanim_donemlerini_karsilastir(
        records, current_period="P2", previous_period="P1"
    )
    assert report.comparison is PeriodComparison.KOTULESIYOR


def test_benzer_donem():
    records = [
        _r("P1", 1, "Modeli koru", 50, 35, 2),
        _r("P1", 2, "Modeli koru", 51, 34, 2),
        _r("P1", 3, "İncele", 49, 36, 1),
        _r("P2", 4, "Modeli koru", 52, 34, 3),
        _r("P2", 5, "Modeli koru", 51, 33, 2),
        _r("P2", 6, "İncele", 50, 35, 2),
    ]
    report = kullanim_donemlerini_karsilastir(
        records, current_period="P2", previous_period="P1"
    )
    assert report.comparison is PeriodComparison.BENZER


def test_metin_raporu():
    records = [
        _r("P1", 1, "Modeli koru", 50, 35, 2),
        _r("P1", 2, "Modeli koru", 51, 34, 2),
        _r("P1", 3, "Modeli koru", 49, 36, 1),
        _r("P2", 4, "Modeli koru", 52, 34, 3),
        _r("P2", 5, "Modeli koru", 51, 33, 2),
        _r("P2", 6, "Modeli koru", 50, 35, 2),
    ]
    report = kullanim_donemlerini_karsilastir(
        records, current_period="P2", previous_period="P1"
    )
    text = donem_karsilastirma_raporunu_metne_cevir(report)
    assert "V2 GERÇEK KULLANIM - DÖNEM KARŞILAŞTIRMASI" in text
    assert "Güncel dönem: P2" in text
    assert "Önceki dönem: P1" in text
