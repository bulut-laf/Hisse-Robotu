from backend.app.prebreakout.prebreakout_v2_calibration_gate import (
    CalibrationGateReport,
    DeteriorationSignal,
)
from backend.app.prebreakout.prebreakout_v2_calibration_validation import (
    CalibrationBeforeAfter,
    CalibrationValidationDecision,
    kontrollu_kalibrasyonu_dogrula,
    kalibrasyon_dogrulama_raporunu_metne_cevir,
)


def _gate(open_: bool):
    return CalibrationGateReport(
        comparison_count=3,
        worsening_count=2,
        latest_comparison=None,
        signal=DeteriorationSignal.KALICI_BOZULMA if open_ else DeteriorationSignal.YOK,
        calibration_review_open=open_,
        reasons=(),
        summary="",
    )


def _cmp(**kw):
    data = dict(
        success_rate_before=45,
        success_rate_after=50,
        false_positive_before=45,
        false_positive_after=38,
        portfolio_return_before=1,
        portfolio_return_after=3,
        max_drawdown_before=8,
        max_drawdown_after=8.5,
        candidate_count_before=100,
        candidate_count_after=85,
    )
    data.update(kw)
    return CalibrationBeforeAfter(**data)


def test_kapi_kapaliysa_degerlendirme_yapilmaz():
    report = kontrollu_kalibrasyonu_dogrula(
        gate_report=_gate(False),
        comparison=_cmp(),
    )
    assert report.decision is CalibrationValidationDecision.KAPI_KAPALI


def test_guclu_iyilesme_uygulama_adayi():
    report = kontrollu_kalibrasyonu_dogrula(
        gate_report=_gate(True),
        comparison=_cmp(),
    )
    assert report.decision is CalibrationValidationDecision.UYGULAMA_ADAYI


def test_iki_temel_bozulma_reddedilir():
    report = kontrollu_kalibrasyonu_dogrula(
        gate_report=_gate(True),
        comparison=_cmp(
            success_rate_after=42,
            portfolio_return_after=-2,
        ),
    )
    assert report.decision is CalibrationValidationDecision.REDDET


def test_asiri_aday_kaybi_guvenlik_sinyali():
    report = kontrollu_kalibrasyonu_dogrula(
        gate_report=_gate(True),
        comparison=_cmp(candidate_count_after=50),
    )
    assert report.candidate_loss_pct == 50.0
    assert report.decision is CalibrationValidationDecision.INCELE


def test_drawdown_bozulmasi_tek_basina_inceleme():
    report = kontrollu_kalibrasyonu_dogrula(
        gate_report=_gate(True),
        comparison=_cmp(max_drawdown_after=11),
    )
    assert report.decision is CalibrationValidationDecision.INCELE


def test_sinirli_iyilesme_inceleme():
    report = kontrollu_kalibrasyonu_dogrula(
        gate_report=_gate(True),
        comparison=_cmp(
            success_rate_after=46,
            false_positive_after=44,
            portfolio_return_after=1.5,
        ),
    )
    assert report.decision is CalibrationValidationDecision.INCELE


def test_metin_karari_icerir():
    report = kontrollu_kalibrasyonu_dogrula(
        gate_report=_gate(True),
        comparison=_cmp(),
    )
    text = kalibrasyon_dogrulama_raporunu_metne_cevir(report)
    assert "V2 GERÇEK KULLANIM - KONTROLLÜ KALİBRASYON DOĞRULAMASI" in text
    assert "Karar: Uygulama adayı" in text
