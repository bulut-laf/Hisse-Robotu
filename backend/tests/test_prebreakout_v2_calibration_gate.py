from backend.app.prebreakout.prebreakout_v2_decision_history import (
    PeriodComparison,
    PeriodComparisonReport,
    PeriodSummary,
)
from backend.app.prebreakout.prebreakout_v2_calibration_gate import (
    CalibrationGatePolicy,
    DeteriorationSignal,
    kalibrasyon_inceleme_kapisini_degerlendir,
    kalibrasyon_kapisi_raporunu_metne_cevir,
)


def _summary(pid):
    return PeriodSummary(pid, 3, "Modeli koru", 0.67, 0.0, 50.0, 30.0, 2.0)


def _report(result):
    return PeriodComparisonReport(
        current_period="P2",
        previous_period="P1",
        comparison=result,
        reasons=(),
        current_summary=_summary("P2"),
        previous_summary=_summary("P1"),
        summary="",
    )


def test_hic_gecmis_yoksa_kapi_kapali():
    r = kalibrasyon_inceleme_kapisini_degerlendir([])
    assert r.calibration_review_open is False
    assert r.signal is DeteriorationSignal.YOK


def test_iki_karsilastirma_yetersiz():
    r = kalibrasyon_inceleme_kapisini_degerlendir([
        _report(PeriodComparison.KOTULESIYOR),
        _report(PeriodComparison.KOTULESIYOR),
    ])
    assert r.calibration_review_open is False
    assert r.signal is DeteriorationSignal.IZLE


def test_uc_karsilastirmada_iki_kotulesme_ve_son_kotuyse_kapi_acilir():
    r = kalibrasyon_inceleme_kapisini_degerlendir([
        _report(PeriodComparison.KOTULESIYOR),
        _report(PeriodComparison.BENZER),
        _report(PeriodComparison.KOTULESIYOR),
    ])
    assert r.calibration_review_open is True
    assert r.signal is DeteriorationSignal.KALICI_BOZULMA


def test_son_donem_kotu_degilse_kapi_acilmaz():
    r = kalibrasyon_inceleme_kapisini_degerlendir([
        _report(PeriodComparison.KOTULESIYOR),
        _report(PeriodComparison.KOTULESIYOR),
        _report(PeriodComparison.BENZER),
    ])
    assert r.calibration_review_open is False


def test_hic_kotulesme_yoksa_sinyal_yok():
    r = kalibrasyon_inceleme_kapisini_degerlendir([
        _report(PeriodComparison.BENZER),
        _report(PeriodComparison.IYILESIYOR),
        _report(PeriodComparison.BENZER),
    ])
    assert r.signal is DeteriorationSignal.YOK
    assert r.calibration_review_open is False


def test_ozel_politika_desteklenir():
    policy = CalibrationGatePolicy(
        minimum_comparisons=2,
        minimum_worsening_count=1,
        require_latest_worsening=False,
    )
    r = kalibrasyon_inceleme_kapisini_degerlendir([
        _report(PeriodComparison.KOTULESIYOR),
        _report(PeriodComparison.BENZER),
    ], policy=policy)
    assert r.calibration_review_open is True


def test_metin_kapi_durumunu_icerir():
    r = kalibrasyon_inceleme_kapisini_degerlendir([
        _report(PeriodComparison.KOTULESIYOR),
        _report(PeriodComparison.BENZER),
        _report(PeriodComparison.KOTULESIYOR),
    ])
    text = kalibrasyon_kapisi_raporunu_metne_cevir(r)
    assert "V2 GERÇEK KULLANIM - KALİBRASYON İNCELEME KAPISI" in text
    assert "Kalibrasyon incelemesi açık: EVET" in text
