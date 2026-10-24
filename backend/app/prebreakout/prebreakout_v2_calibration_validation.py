from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from backend.app.prebreakout.prebreakout_v2_calibration_gate import CalibrationGateReport


class CalibrationValidationDecision(str, Enum):
    KAPI_KAPALI = "Kapı kapalı"
    REDDET = "Reddet"
    INCELE = "İncele"
    UYGULAMA_ADAYI = "Uygulama adayı"


@dataclass(frozen=True)
class CalibrationBeforeAfter:
    success_rate_before: float
    success_rate_after: float
    false_positive_before: float
    false_positive_after: float
    portfolio_return_before: float
    portfolio_return_after: float
    max_drawdown_before: float
    max_drawdown_after: float
    candidate_count_before: int
    candidate_count_after: int


@dataclass(frozen=True)
class CalibrationValidationPolicy:
    minimum_success_improvement_pct: float = 3.0
    minimum_false_positive_improvement_pct: float = 3.0
    minimum_portfolio_improvement_pct: float = 1.0
    maximum_drawdown_worsening_pct: float = 1.5
    maximum_candidate_loss_pct: float = 35.0


@dataclass(frozen=True)
class CalibrationValidationReport:
    gate_open: bool
    decision: CalibrationValidationDecision
    success_delta: float
    false_positive_delta: float
    portfolio_delta: float
    drawdown_delta: float
    candidate_loss_pct: float
    reasons: tuple[str, ...]
    summary: str


def kontrollu_kalibrasyonu_dogrula(
    *,
    gate_report: CalibrationGateReport,
    comparison: CalibrationBeforeAfter,
    policy: CalibrationValidationPolicy | None = None,
) -> CalibrationValidationReport:
    policy = policy or CalibrationValidationPolicy()

    success_delta = round(comparison.success_rate_after - comparison.success_rate_before, 4)
    false_positive_delta = round(
        comparison.false_positive_before - comparison.false_positive_after, 4
    )
    portfolio_delta = round(
        comparison.portfolio_return_after - comparison.portfolio_return_before, 4
    )
    drawdown_delta = round(
        comparison.max_drawdown_after - comparison.max_drawdown_before, 4
    )

    if comparison.candidate_count_before <= 0:
        candidate_loss_pct = 0.0
    else:
        candidate_loss_pct = round(
            max(0, comparison.candidate_count_before - comparison.candidate_count_after)
            / comparison.candidate_count_before
            * 100,
            4,
        )

    if not gate_report.calibration_review_open:
        return CalibrationValidationReport(
            gate_open=False,
            decision=CalibrationValidationDecision.KAPI_KAPALI,
            success_delta=success_delta,
            false_positive_delta=false_positive_delta,
            portfolio_delta=portfolio_delta,
            drawdown_delta=drawdown_delta,
            candidate_loss_pct=candidate_loss_pct,
            reasons=("Kalibrasyon inceleme kapısı açık değil.",),
            summary="Mevcut model korunmalı; kalibrasyon sonucu üretime alınmamalı.",
        )

    reasons: list[str] = []
    positive = 0
    negative = 0

    if success_delta >= policy.minimum_success_improvement_pct:
        positive += 1
        reasons.append(f"Başarı oranı +{success_delta:.1f} puan iyileşti.")
    elif success_delta < 0:
        negative += 1
        reasons.append(f"Başarı oranı {success_delta:.1f} puan kötüleşti.")

    if false_positive_delta >= policy.minimum_false_positive_improvement_pct:
        positive += 1
        reasons.append(f"Yanlış pozitif oranı {false_positive_delta:.1f} puan iyileşti.")
    elif false_positive_delta < 0:
        negative += 1
        reasons.append(
            f"Yanlış pozitif oranı {abs(false_positive_delta):.1f} puan kötüleşti."
        )

    if portfolio_delta >= policy.minimum_portfolio_improvement_pct:
        positive += 1
        reasons.append(f"Deneme portföyü getirisi +{portfolio_delta:.1f} puan iyileşti.")
    elif portfolio_delta < 0:
        negative += 1
        reasons.append(f"Deneme portföyü getirisi {portfolio_delta:.1f} puan kötüleşti.")

    if drawdown_delta > policy.maximum_drawdown_worsening_pct:
        negative += 1
        reasons.append(
            f"Maksimum düşüş {drawdown_delta:.1f} puan arttı; güvenlik sınırı aşıldı."
        )

    if candidate_loss_pct > policy.maximum_candidate_loss_pct:
        negative += 1
        reasons.append(
            f"Aday sayısı %{candidate_loss_pct:.1f} azaldı; kapsam kaybı fazla."
        )

    if negative >= 2:
        decision = CalibrationValidationDecision.REDDET
        summary = (
            "Kalibrasyon birden fazla temel ölçütte bozulma yarattı. "
            "Öneri reddedilmeli ve mevcut model korunmalı."
        )
    elif positive >= 3 and negative == 0:
        decision = CalibrationValidationDecision.UYGULAMA_ADAYI
        reasons.append("En az üç temel ölçütte iyileşme var ve güvenlik ihlali yok.")
        summary = (
            "Kalibrasyon tarihsel/canlı karşılaştırmada anlamlı iyileşme gösteriyor. "
            "Yine de otomatik uygulanmamalı; kontrollü uygulama adayı kabul edilmeli."
        )
    else:
        decision = CalibrationValidationDecision.INCELE
        if not reasons:
            reasons.append("Farklar karar eşiklerinin altında kaldı.")
        summary = (
            "Kalibrasyon sonucu net değil. Mevcut model korunmalı ve daha fazla veriyle "
            "karşılaştırma sürdürülmeli."
        )

    return CalibrationValidationReport(
        gate_open=True,
        decision=decision,
        success_delta=success_delta,
        false_positive_delta=false_positive_delta,
        portfolio_delta=portfolio_delta,
        drawdown_delta=drawdown_delta,
        candidate_loss_pct=candidate_loss_pct,
        reasons=tuple(reasons),
        summary=summary,
    )


def kalibrasyon_dogrulama_raporunu_metne_cevir(
    report: CalibrationValidationReport,
) -> str:
    return "\n".join(
        [
            "V2 GERÇEK KULLANIM - KONTROLLÜ KALİBRASYON DOĞRULAMASI",
            f"Kalibrasyon kapısı açık: {'EVET' if report.gate_open else 'HAYIR'}",
            f"Karar: {report.decision.value}",
            f"Başarı oranı farkı: {report.success_delta:+.2f} puan",
            f"Yanlış pozitif iyileşmesi: {report.false_positive_delta:+.2f} puan",
            f"Portföy getirisi farkı: {report.portfolio_delta:+.2f} puan",
            f"Maksimum düşüş farkı: {report.drawdown_delta:+.2f} puan",
            f"Aday kaybı: %{report.candidate_loss_pct:.2f}",
            "Nedenler:",
            *[f"- {x}" for x in report.reasons],
            f"Özet: {report.summary}",
        ]
    )
