from backend.app.prebreakout.prebreakout_live_performance import LiveHorizonPerformance, LivePerformanceLabel, LiveSignalPerformance
from backend.app.prebreakout.prebreakout_performance_comparison import performans_karsilastirmasini_hesapla, performans_karsilastirmasini_tabloya_cevir


def _record(signal_id: str, stage: str, label: LivePerformanceLabel, close: float | None, maximum: float | None):
    return LiveSignalPerformance(signal_id, "THYAO.IS", "2026-01-01", stage, 100.0, "2026-02-01", 20, label, (LiveHorizonPerformance(20, 20, close, maximum, -2.0, -3.0),), "test")


def test_asama_bazinda_karsilastirma_hesaplanir():
    rows = performans_karsilastirmasini_hesapla((
        _record("1", "E2", LivePerformanceLabel.BASARILI, 6.0, 12.0),
        _record("2", "E2", LivePerformanceLabel.BASARISIZ, -6.0, 1.0),
        _record("3", "E3", LivePerformanceLabel.SINIRLI_HAREKET, 2.0, 7.0),
    ))
    e2 = next(item for item in rows if item.dimension == "Aşama" and item.group == "E2")
    assert e2.measured_count == 2
    assert e2.success_rate_pct == 50.0
    assert e2.false_positive_rate_pct == 50.0


def test_olculemeyen_kayit_oranlari_bozmaz():
    rows = performans_karsilastirmasini_hesapla((_record("1", "E4", LivePerformanceLabel.OLCULEMIYOR, None, None),))
    assert rows[0].measured_count == 0
    assert rows[0].success_rate_pct is None
    assert rows[0].unmeasured_count == 1


def test_esik_sektor_ve_rejim_kirilimlari_uretilir():
    records = (_record("1", "E2", LivePerformanceLabel.BASARILI, 6.0, 12.0), _record("2", "E3", LivePerformanceLabel.BASARISIZ, -6.0, 2.0))
    rows = performans_karsilastirmasini_hesapla(records, sectors={"1":"Ulaştırma","2":"Enerji"}, market_regimes={"1":"Pozitif","2":"Negatif"}, threshold_modes={"1":"Kalibre","2":"Varsayılan"})
    assert {item.dimension for item in rows} >= {"Aşama", "Eşik politikası", "Sektör", "Piyasa rejimi"}


def test_karsilastirma_tablosu_beklenen_sutunlari_icerir():
    rows = performans_karsilastirmasini_hesapla((_record("1", "E2", LivePerformanceLabel.BASARILI, 6.0, 12.0),))
    table = performans_karsilastirmasini_tabloya_cevir(rows)
    assert "Yanlış pozitif (%)" in table.columns
    assert "Ort. 20G kapanış (%)" in table.columns
