from backend.app.prebreakout.prebreakout_v2_calibration_validation import (
    CalibrationValidationDecision,
    CalibrationValidationReport,
)
from backend.app.prebreakout.prebreakout_v2_decision_stability import (
    DecisionStability,
    DecisionStabilityReport,
)
from backend.app.prebreakout.prebreakout_v2_live_closure import (
    V2ClosureStatus,
    v2_canli_gozlem_fazini_kapat,
    v2_kapanis_raporunu_metne_cevir,
)
from backend.app.prebreakout.prebreakout_v2_sample_adequacy import (
    SampleAdequacyStatus,
    SampleReadiness,
)


def _sample(ready=True):
    return SampleAdequacyStatus(
        observation_days=30 if ready else 10,
        measured_candidate_count=60 if ready else 10,
        mature_20d_candidate_count=30 if ready else 2,
        reliable_regime_group_count=2 if ready else 1,
        covered_stage_count=3 if ready else 2,
        readiness=(
            SampleReadiness.ILK_DEGERLENDIRMEYE_HAZIR
            if ready
            else SampleReadiness.IZLEMEYE_DEVAM
        ),
        first_evaluation_ready=ready,
        completion_ratio=1.0 if ready else 0.4,
        missing_conditions=() if ready else ("Eksik",),
        summary="",
    )


def _stability(stable=True):
    return DecisionStabilityReport(
        snapshot_count=3,
        current_decision=None,
        dominant_decision=None,
        dominant_share=1.0 if stable else 0.5,
        stability=DecisionStability.KARARLI if stable else DecisionStability.DALGALI,
        decision_changes=0 if stable else 2,
        model_change_allowed=False,
        reasons=(),
        summary="",
    )


def _cal(decision):
    return CalibrationValidationReport(
        gate_open=True,
        decision=decision,
        success_delta=4,
        false_positive_delta=4,
        portfolio_delta=2,
        drawdown_delta=0,
        candidate_loss_pct=10,
        reasons=(),
        summary="",
    )


def test_teknik_test_basarisizsa_kapanmaz():
    report = v2_canli_gozlem_fazini_kapat(
        technical_tests_ok=False,
        sample_status=_sample(),
        stability_report=_stability(),
    )
    assert report.closure_status is V2ClosureStatus.INCELEME_GEREKLI


def test_orneklem_yetersizse_gozleme_devam():
    report = v2_canli_gozlem_fazini_kapat(
        technical_tests_ok=True,
        sample_status=_sample(False),
        stability_report=_stability(),
    )
    assert report.closure_status is V2ClosureStatus.GOZLEME_DEVAM


def test_karar_dalgaliysa_gozleme_devam():
    report = v2_canli_gozlem_fazini_kapat(
        technical_tests_ok=True,
        sample_status=_sample(True),
        stability_report=_stability(False),
    )
    assert report.closure_status is V2ClosureStatus.GOZLEME_DEVAM


def test_kalibrasyon_uygulama_adayi_inceleme_gerektirir():
    report = v2_canli_gozlem_fazini_kapat(
        technical_tests_ok=True,
        sample_status=_sample(True),
        stability_report=_stability(True),
        calibration_report=_cal(CalibrationValidationDecision.UYGULAMA_ADAYI),
    )
    assert report.closure_status is V2ClosureStatus.INCELEME_GEREKLI
    assert report.production_model_change_required is False


def test_kalibrasyon_reddedildiyse_model_korunur():
    report = v2_canli_gozlem_fazini_kapat(
        technical_tests_ok=True,
        sample_status=_sample(True),
        stability_report=_stability(True),
        calibration_report=_cal(CalibrationValidationDecision.REDDET),
    )
    assert report.closure_status is V2ClosureStatus.KARARLI_SURUM


def test_kalibrasyon_yoksa_kararli_kapanabilir():
    report = v2_canli_gozlem_fazini_kapat(
        technical_tests_ok=True,
        sample_status=_sample(True),
        stability_report=_stability(True),
    )
    assert report.closure_status is V2ClosureStatus.KARARLI_SURUM


def test_metin_raporu():
    report = v2_canli_gozlem_fazini_kapat(
        technical_tests_ok=True,
        sample_status=_sample(True),
        stability_report=_stability(True),
    )
    text = v2_kapanis_raporunu_metne_cevir(report)
    assert "HİSSE ROBOTU - V2 CANLI GÖZLEM FAZI KAPANIŞI" in text
    assert "Kapanış durumu: Kararlı sürüm" in text
    assert "Üretim modeli değişikliği gerekli: HAYIR" in text
