from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from backend.app.prebreakout.prebreakout_v2_first_live_evaluation import (
    FirstLiveEvaluation,
    ModelDecision,
)


class DecisionStability(str, Enum):
    YETERSIZ_GECMIS = "Yetersiz geçmiş"
    KARARLI = "Kararlı"
    DALGALI = "Dalgalı"
    BOZULUYOR = "Bozuluyor"


@dataclass(frozen=True)
class DecisionSnapshot:
    observation_day: int
    decision: ModelDecision
    success_rate_pct: float | None
    false_positive_rate_pct: float | None
    portfolio_return_pct: float | None


@dataclass(frozen=True)
class DecisionStabilityPolicy:
    minimum_snapshots: int = 3
    stable_share_threshold: float = 0.67
    deterioration_window: int = 3


@dataclass(frozen=True)
class DecisionStabilityReport:
    snapshot_count: int
    current_decision: ModelDecision | None
    dominant_decision: ModelDecision | None
    dominant_share: float
    stability: DecisionStability
    decision_changes: int
    model_change_allowed: bool
    reasons: tuple[str, ...]
    summary: str


def snapshot_olustur(
    evaluation: FirstLiveEvaluation,
    *,
    observation_day: int,
) -> DecisionSnapshot:
    return DecisionSnapshot(
        observation_day=max(0, int(observation_day)),
        decision=evaluation.model_decision,
        success_rate_pct=evaluation.success_rate_pct,
        false_positive_rate_pct=evaluation.false_positive_rate_pct,
        portfolio_return_pct=evaluation.portfolio_return_pct,
    )


def karar_istikrarini_degerlendir(
    snapshots: tuple[DecisionSnapshot, ...] | list[DecisionSnapshot],
    *,
    policy: DecisionStabilityPolicy | None = None,
) -> DecisionStabilityReport:
    policy = policy or DecisionStabilityPolicy()
    ordered = sorted(snapshots, key=lambda x: x.observation_day)
    n = len(ordered)

    if n == 0:
        return DecisionStabilityReport(
            snapshot_count=0,
            current_decision=None,
            dominant_decision=None,
            dominant_share=0.0,
            stability=DecisionStability.YETERSIZ_GECMIS,
            decision_changes=0,
            model_change_allowed=False,
            reasons=("Henüz karar geçmişi yok.",),
            summary="Model kararı için geçmiş birikimi sürdürülmeli.",
        )

    current = ordered[-1].decision
    changes = sum(
        1 for a, b in zip(ordered, ordered[1:]) if a.decision is not b.decision
    )

    counts: dict[ModelDecision, int] = {}
    for item in ordered:
        counts[item.decision] = counts.get(item.decision, 0) + 1
    dominant = max(counts, key=counts.get)
    dominant_share = round(counts[dominant] / n, 4)

    if n < policy.minimum_snapshots:
        return DecisionStabilityReport(
            snapshot_count=n,
            current_decision=current,
            dominant_decision=dominant,
            dominant_share=dominant_share,
            stability=DecisionStability.YETERSIZ_GECMIS,
            decision_changes=changes,
            model_change_allowed=False,
            reasons=(f"En az {policy.minimum_snapshots} karar gözlemi gerekli.",),
            summary="Tek veya az sayıda değerlendirmeyle model değiştirilmemeli.",
        )

    recent = ordered[-policy.deterioration_window :]
    recent_bad = [
        x for x in recent
        if x.decision in (ModelDecision.INCELE, ModelDecision.KALIBRASYON_ADAYI)
    ]
    recent_calibration = [
        x for x in recent if x.decision is ModelDecision.KALIBRASYON_ADAYI
    ]

    reasons: list[str] = []

    if (
        len(recent) >= policy.deterioration_window
        and len(recent_bad) == len(recent)
        and len(recent_calibration) >= 2
    ):
        stability = DecisionStability.BOZULUYOR
        reasons.append("Son karar penceresinde zayıflık kalıcı hâle geliyor.")
        allow_change = True
        summary = (
            "Model performansındaki bozulma tek günlük değil. Kontrollü kalibrasyon "
            "incelemesi başlatılabilir; otomatik eşik değişikliği yapılmamalı."
        )
    elif dominant_share >= policy.stable_share_threshold and current is dominant:
        stability = DecisionStability.KARARLI
        reasons.append(
            f"Baskın karar payı %{dominant_share * 100:.1f} ve son karar baskın yönle uyumlu."
        )
        allow_change = current is ModelDecision.KALIBRASYON_ADAYI
        if current is ModelDecision.MODELI_KORU:
            summary = "Karar istikrarlı: mevcut V2 modeli korunmalı."
        elif current is ModelDecision.INCELE:
            summary = "İnceleme kararı istikrarlı; neden analizi sürdürülmeli."
        else:
            summary = (
                "Kalibrasyon adayı kararı istikrarlı. Kontrollü kalibrasyon değerlendirmesi yapılabilir."
            )
    else:
        stability = DecisionStability.DALGALI
        reasons.append(
            "Karar geçmişi yeterli olsa da tek bir baskın ve kararlı yön oluşmadı."
        )
        allow_change = False
        summary = (
            "Karar dalgalı. Model değişikliği yapılmadan daha fazla gerçek kullanım verisi toplanmalı."
        )

    return DecisionStabilityReport(
        snapshot_count=n,
        current_decision=current,
        dominant_decision=dominant,
        dominant_share=dominant_share,
        stability=stability,
        decision_changes=changes,
        model_change_allowed=allow_change,
        reasons=tuple(reasons),
        summary=summary,
    )


def karar_istikrar_raporunu_metne_cevir(report: DecisionStabilityReport) -> str:
    return "\n".join(
        [
            "V2 GERÇEK KULLANIM - KARAR İSTİKRARI",
            f"Gözlem sayısı: {report.snapshot_count}",
            f"Güncel karar: {report.current_decision.value if report.current_decision else 'Yok'}",
            f"Baskın karar: {report.dominant_decision.value if report.dominant_decision else 'Yok'}",
            f"Baskın karar payı: %{report.dominant_share * 100:.1f}",
            f"Karar değişimi: {report.decision_changes}",
            f"İstikrar: {report.stability.value}",
            f"Model değişikliği değerlendirilebilir: {'EVET' if report.model_change_allowed else 'HAYIR'}",
            "Nedenler:",
            *[f"- {reason}" for reason in report.reasons],
            f"Özet: {report.summary}",
        ]
    )
