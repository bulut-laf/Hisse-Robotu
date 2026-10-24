from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ObservationDecision(str, Enum):
    VERI_BIRIKTIR = "Veri biriktir"
    DEGERLENDIRMEYE_HAZIR = "Değerlendirmeye hazır"
    MODEL_DEGISIKLIGINI_DONDUR = "Model değişikliğini dondur"


@dataclass(frozen=True)
class ObservationPolicy:
    minimum_measured_candidates: int = 30
    minimum_reliable_regime_groups: int = 2
    minimum_observation_days: int = 20


@dataclass(frozen=True)
class V2ObservationStatus:
    observation_days: int
    measured_candidate_count: int
    reliable_regime_group_count: int
    evidence_ready: bool
    decision: ObservationDecision
    model_change_allowed: bool
    remaining_candidate_count: int
    remaining_observation_days: int
    warnings: tuple[str, ...]
    summary: str


def v2_gozlem_durumunu_degerlendir(
    *,
    observation_days: int,
    measured_candidate_count: int,
    reliable_regime_group_count: int,
    technical_ready: bool = True,
    policy: ObservationPolicy | None = None,
) -> V2ObservationStatus:
    """V2 sonrası canlı gözlem döneminin yeterliliğini değerlendirir.

    Bu katman üretim eşiklerini değiştirmez. Amaç, model değişikliğini ancak
    yeterli gerçek kullanım kanıtı biriktiğinde yeniden gündeme almaktır.
    """
    policy = policy or ObservationPolicy()

    days = max(0, int(observation_days))
    measured = max(0, int(measured_candidate_count))
    reliable = max(0, int(reliable_regime_group_count))

    remaining_candidates = max(0, policy.minimum_measured_candidates - measured)
    remaining_days = max(0, policy.minimum_observation_days - days)

    warnings: list[str] = []
    if not technical_ready:
        warnings.append("V2 teknik sağlık kontrolü hazır değil")
    if remaining_days:
        warnings.append(f"Canlı gözlem süresi için en az {remaining_days} gün daha gerekli")
    if remaining_candidates:
        warnings.append(f"Gerçek sonuç değerlendirmesi için en az {remaining_candidates} ölçülmüş aday daha gerekli")
    if reliable < policy.minimum_reliable_regime_groups:
        warnings.append("Piyasa rejimi kırılımında güvenilir grup sayısı henüz yetersiz")

    evidence_ready = (
        technical_ready
        and days >= policy.minimum_observation_days
        and measured >= policy.minimum_measured_candidates
        and reliable >= policy.minimum_reliable_regime_groups
    )

    if not technical_ready:
        decision = ObservationDecision.MODEL_DEGISIKLIGINI_DONDUR
        summary = "Teknik sağlık tamamlanmadan model değişikliği yapılmamalı; önce operasyon sorunu çözülmeli."
    elif evidence_ready:
        decision = ObservationDecision.DEGERLENDIRMEYE_HAZIR
        summary = "Canlı gözlem eşiği karşılandı; model performansı yeniden değerlendirilebilir, ancak otomatik eşik değişikliği yapılmaz."
    else:
        decision = ObservationDecision.VERI_BIRIKTIR
        summary = "Gerçek kullanım kanıtı henüz yeterli değil; mevcut V2 modeli korunarak veri biriktirilmeli."

    return V2ObservationStatus(
        observation_days=days,
        measured_candidate_count=measured,
        reliable_regime_group_count=reliable,
        evidence_ready=evidence_ready,
        decision=decision,
        model_change_allowed=False,
        remaining_candidate_count=remaining_candidates,
        remaining_observation_days=remaining_days,
        warnings=tuple(warnings),
        summary=summary,
    )


def v2_gozlem_durumunu_metne_cevir(status: V2ObservationStatus) -> str:
    warning_text = "Yok" if not status.warnings else " | ".join(status.warnings)
    return "\n".join(
        [
            "GERÇEK KULLANIM V2 - CANLI GÖZLEM DURUMU",
            f"Gözlem günü: {status.observation_days}",
            f"Ölçülen E2-E4 aday: {status.measured_candidate_count}",
            f"Güvenilir rejim/aşama grubu: {status.reliable_regime_group_count}",
            f"Kanıt değerlendirmeye hazır: {'EVET' if status.evidence_ready else 'HAYIR'}",
            f"Karar: {status.decision.value}",
            "Model değişikliği: DONDURULDU",
            f"Kalan ölçülmüş aday: {status.remaining_candidate_count}",
            f"Kalan gözlem günü: {status.remaining_observation_days}",
            f"Uyarılar: {warning_text}",
            f"Özet: {status.summary}",
        ]
    )
