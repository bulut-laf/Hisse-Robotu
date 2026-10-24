from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from backend.app.prebreakout.prebreakout_v2_calibration_validation import (
    CalibrationValidationDecision,
    CalibrationValidationReport,
)
from backend.app.prebreakout.prebreakout_v2_decision_stability import (
    DecisionStability,
    DecisionStabilityReport,
)
from backend.app.prebreakout.prebreakout_v2_sample_adequacy import (
    SampleAdequacyStatus,
)


class V2ClosureStatus(str, Enum):
    KARARLI_SURUM = "Kararlı sürüm"
    GOZLEME_DEVAM = "Gözleme devam"
    INCELEME_GEREKLI = "İnceleme gerekli"


@dataclass(frozen=True)
class V2ClosureReport:
    technical_tests_ok: bool
    sample_ready: bool
    decision_stable: bool
    calibration_state: str
    closure_status: V2ClosureStatus
    production_model_change_required: bool
    reasons: tuple[str, ...]
    summary: str


def v2_canli_gozlem_fazini_kapat(
    *,
    technical_tests_ok: bool,
    sample_status: SampleAdequacyStatus,
    stability_report: DecisionStabilityReport,
    calibration_report: CalibrationValidationReport | None = None,
) -> V2ClosureReport:
    reasons: list[str] = []

    if not technical_tests_ok:
        reasons.append("Teknik test zinciri başarısız.")
        return V2ClosureReport(
            technical_tests_ok=False,
            sample_ready=sample_status.first_evaluation_ready,
            decision_stable=False,
            calibration_state="Değerlendirilmedi",
            closure_status=V2ClosureStatus.INCELEME_GEREKLI,
            production_model_change_required=False,
            reasons=tuple(reasons),
            summary="V2 canlı gözlem fazı teknik olarak kapatılamaz.",
        )

    sample_ready = sample_status.first_evaluation_ready
    decision_stable = stability_report.stability in {
        DecisionStability.KARARLI,
        DecisionStability.BOZULUYOR,
    }

    calibration_state = (
        calibration_report.decision.value
        if calibration_report is not None
        else "Kalibrasyon incelemesi yok"
    )

    if not sample_ready:
        reasons.append("İlk gerçek kullanım değerlendirmesi için örneklem henüz yeterli değil.")
        status = V2ClosureStatus.GOZLEME_DEVAM
        change_required = False
        summary = "Yazılım katmanı kararlı; model performansı için canlı veri birikimi sürdürülmeli."
    elif not decision_stable:
        reasons.append("Gerçek kullanım karar geçmişi henüz kararlı değil.")
        status = V2ClosureStatus.GOZLEME_DEVAM
        change_required = False
        summary = "Teknik altyapı hazır; model kararı dalgalı olduğu için eşikler değiştirilmeden gözleme devam edilmeli."
    elif (
        calibration_report is not None
        and calibration_report.decision is CalibrationValidationDecision.UYGULAMA_ADAYI
    ):
        reasons.append("Kontrollü kalibrasyon doğrulamasında uygulama adayı oluştu.")
        status = V2ClosureStatus.INCELEME_GEREKLI
        change_required = False
        summary = "Kalibrasyon adayı ayrıca kontrollü uygulama incelemesi gerektiriyor; otomatik üretim değişikliği yapılmamalı."
    elif (
        calibration_report is not None
        and calibration_report.decision is CalibrationValidationDecision.REDDET
    ):
        reasons.append("Kalibrasyon önerisi reddedildi; mevcut üretim modeli korunuyor.")
        status = V2ClosureStatus.KARARLI_SURUM
        change_required = False
        summary = "V2 canlı gözlem fazı mevcut model korunarak kararlı sürüm olarak kapatılabilir."
    else:
        reasons.append("Teknik testler, örneklem yeterliliği ve karar istikrarı kabul edilebilir durumda.")
        status = V2ClosureStatus.KARARLI_SURUM
        change_required = False
        summary = "V2 canlı gözlem fazı kararlı sürüm olarak kapatılabilir."

    return V2ClosureReport(
        technical_tests_ok=True,
        sample_ready=sample_ready,
        decision_stable=decision_stable,
        calibration_state=calibration_state,
        closure_status=status,
        production_model_change_required=change_required,
        reasons=tuple(reasons),
        summary=summary,
    )


def v2_kapanis_raporunu_metne_cevir(report: V2ClosureReport) -> str:
    return "\n".join(
        [
            "HİSSE ROBOTU - V2 CANLI GÖZLEM FAZI KAPANIŞI",
            f"Teknik testler: {'BAŞARILI' if report.technical_tests_ok else 'BAŞARISIZ'}",
            f"Örneklem hazır: {'EVET' if report.sample_ready else 'HAYIR'}",
            f"Karar istikrarlı: {'EVET' if report.decision_stable else 'HAYIR'}",
            f"Kalibrasyon durumu: {report.calibration_state}",
            f"Kapanış durumu: {report.closure_status.value}",
            f"Üretim modeli değişikliği gerekli: {'EVET' if report.production_model_change_required else 'HAYIR'}",
            "Nedenler:",
            *[f"- {x}" for x in report.reasons],
            f"Özet: {report.summary}",
        ]
    )
