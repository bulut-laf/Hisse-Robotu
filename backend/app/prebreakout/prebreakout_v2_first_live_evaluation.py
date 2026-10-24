from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from backend.app.prebreakout.prebreakout_v2_sample_adequacy import (
    SampleAdequacyStatus,
    SampleReadiness,
)


class ModelDecision(str, Enum):
    MODELI_KORU = "Modeli koru"
    INCELE = "İncele"
    KALIBRASYON_ADAYI = "Kalibrasyon adayı"


@dataclass(frozen=True)
class FirstLiveEvaluation:
    sample_ready: bool
    measured_candidate_count: int
    mature_20d_candidate_count: int
    success_rate_pct: float | None
    false_positive_rate_pct: float | None
    average_trigger_sessions: float | None
    portfolio_return_pct: float | None
    max_drawdown_pct: float | None
    model_decision: ModelDecision
    reasons: tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class FirstLiveEvaluationPolicy:
    minimum_success_rate_pct: float = 45.0
    maximum_false_positive_rate_pct: float = 45.0
    maximum_average_trigger_sessions: float = 7.0
    maximum_drawdown_pct: float = 12.0
    minimum_portfolio_return_pct: float = 0.0


def ilk_gercek_kullanim_degerlendirmesini_yap(
    *,
    sample_status: SampleAdequacyStatus,
    measured_candidate_count: int,
    mature_20d_candidate_count: int,
    success_rate_pct: float | None,
    false_positive_rate_pct: float | None,
    average_trigger_sessions: float | None,
    portfolio_return_pct: float | None,
    max_drawdown_pct: float | None,
    policy: FirstLiveEvaluationPolicy | None = None,
) -> FirstLiveEvaluation:
    policy = policy or FirstLiveEvaluationPolicy()

    if (
        not sample_status.first_evaluation_ready
        or sample_status.readiness is not SampleReadiness.ILK_DEGERLENDIRMEYE_HAZIR
    ):
        return FirstLiveEvaluation(
            sample_ready=False,
            measured_candidate_count=max(0, int(measured_candidate_count)),
            mature_20d_candidate_count=max(0, int(mature_20d_candidate_count)),
            success_rate_pct=success_rate_pct,
            false_positive_rate_pct=false_positive_rate_pct,
            average_trigger_sessions=average_trigger_sessions,
            portfolio_return_pct=portfolio_return_pct,
            max_drawdown_pct=max_drawdown_pct,
            model_decision=ModelDecision.MODELI_KORU,
            reasons=("Canlı örneklem ilk değerlendirme için henüz yeterli değil.",),
            summary="Model değiştirilmeden canlı gözleme devam edilmeli.",
        )

    reasons: list[str] = []
    weak_count = 0

    if success_rate_pct is None:
        reasons.append("Başarı oranı ölçülemiyor.")
        weak_count += 1
    elif success_rate_pct < policy.minimum_success_rate_pct:
        reasons.append(
            f"Başarı oranı %{success_rate_pct:.1f}; hedef %{policy.minimum_success_rate_pct:.1f} altında."
        )
        weak_count += 1

    if false_positive_rate_pct is None:
        reasons.append("Yanlış pozitif oranı ölçülemiyor.")
        weak_count += 1
    elif false_positive_rate_pct > policy.maximum_false_positive_rate_pct:
        reasons.append(
            f"Yanlış pozitif oranı %{false_positive_rate_pct:.1f}; üst sınır %{policy.maximum_false_positive_rate_pct:.1f} üzerinde."
        )
        weak_count += 1

    if average_trigger_sessions is None:
        reasons.append("Ortalama tetiklenme süresi ölçülemiyor.")
        weak_count += 1
    elif average_trigger_sessions > policy.maximum_average_trigger_sessions:
        reasons.append(
            f"Ortalama tetiklenme {average_trigger_sessions:.1f} seans; hedef {policy.maximum_average_trigger_sessions:.1f} seansın üzerinde."
        )
        weak_count += 1

    if portfolio_return_pct is None:
        reasons.append("Deneme portföyü getirisi ölçülemiyor.")
        weak_count += 1
    elif portfolio_return_pct < policy.minimum_portfolio_return_pct:
        reasons.append(
            f"Deneme portföyü getirisi %{portfolio_return_pct:.1f}; minimum %{policy.minimum_portfolio_return_pct:.1f} altında."
        )
        weak_count += 1

    if max_drawdown_pct is None:
        reasons.append("Maksimum düşüş ölçülemiyor.")
        weak_count += 1
    elif max_drawdown_pct > policy.maximum_drawdown_pct:
        reasons.append(
            f"Maksimum düşüş %{max_drawdown_pct:.1f}; üst sınır %{policy.maximum_drawdown_pct:.1f} üzerinde."
        )
        weak_count += 1

    if weak_count == 0:
        decision = ModelDecision.MODELI_KORU
        reasons.append("Temel canlı performans ölçütleri kabul sınırları içinde.")
        summary = "İlk gerçek kullanım sonuçları mevcut V2 modelini korumayı destekliyor."
    elif weak_count <= 2:
        decision = ModelDecision.INCELE
        summary = "Model hemen değiştirilmemeli; zayıf ölçütler ayrıntılı incelenmeli."
    else:
        decision = ModelDecision.KALIBRASYON_ADAYI
        summary = (
            "Birden fazla temel ölçüt zayıf. Model otomatik değiştirilmemeli; "
            "kontrollü kalibrasyon için aday kabul edilmeli."
        )

    return FirstLiveEvaluation(
        sample_ready=True,
        measured_candidate_count=max(0, int(measured_candidate_count)),
        mature_20d_candidate_count=max(0, int(mature_20d_candidate_count)),
        success_rate_pct=success_rate_pct,
        false_positive_rate_pct=false_positive_rate_pct,
        average_trigger_sessions=average_trigger_sessions,
        portfolio_return_pct=portfolio_return_pct,
        max_drawdown_pct=max_drawdown_pct,
        model_decision=decision,
        reasons=tuple(reasons),
        summary=summary,
    )


def ilk_gercek_kullanim_raporunu_metne_cevir(report: FirstLiveEvaluation) -> str:
    def fmt(value: float | None, suffix: str = "") -> str:
        return "Ölçülemiyor" if value is None else f"{value:.2f}{suffix}"

    return "\n".join(
        [
            "V2 İLK GERÇEK KULLANIM DEĞERLENDİRMESİ",
            f"Örneklem hazır: {'EVET' if report.sample_ready else 'HAYIR'}",
            f"Karar: {report.model_decision.value}",
            f"Ölçülmüş aday: {report.measured_candidate_count}",
            f"20 günlük olgun sonuç: {report.mature_20d_candidate_count}",
            f"Başarı oranı: {fmt(report.success_rate_pct, '%')}",
            f"Yanlış pozitif oranı: {fmt(report.false_positive_rate_pct, '%')}",
            f"Ortalama tetiklenme süresi: {fmt(report.average_trigger_sessions, ' seans')}",
            f"Deneme portföyü getirisi: {fmt(report.portfolio_return_pct, '%')}",
            f"Maksimum düşüş: {fmt(report.max_drawdown_pct, '%')}",
            "Nedenler:",
            *[f"- {reason}" for reason in report.reasons],
            f"Özet: {report.summary}",
        ]
    )
