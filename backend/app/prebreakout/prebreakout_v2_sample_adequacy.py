from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from backend.app.prebreakout.prebreakout_v2_observation import V2ObservationStatus


class SampleReadiness(str, Enum):
    IZLEMEYE_DEVAM = "İzlemeye devam"
    ON_DEGERLENDIRME = "Ön değerlendirme"
    ILK_DEGERLENDIRMEYE_HAZIR = "İlk değerlendirmeye hazır"


@dataclass(frozen=True)
class SampleAdequacyPolicy:
    minimum_observation_days: int = 30
    minimum_measured_candidates: int = 60
    minimum_mature_20d_candidates: int = 30
    minimum_reliable_regime_groups: int = 2
    minimum_stage_coverage: int = 3


@dataclass(frozen=True)
class SampleAdequacyStatus:
    observation_days: int
    measured_candidate_count: int
    mature_20d_candidate_count: int
    reliable_regime_group_count: int
    covered_stage_count: int
    readiness: SampleReadiness
    first_evaluation_ready: bool
    completion_ratio: float
    missing_conditions: tuple[str, ...]
    summary: str


def _ratio(value: int, target: int) -> float:
    if target <= 0:
        return 1.0
    return min(1.0, max(0.0, value / target))


def canli_orneklem_yeterliligini_degerlendir(
    *,
    observation_days: int,
    measured_candidate_count: int,
    mature_20d_candidate_count: int,
    reliable_regime_group_count: int,
    covered_stage_count: int,
    technical_ready: bool = True,
    policy: SampleAdequacyPolicy | None = None,
) -> SampleAdequacyStatus:
    """Canlı gözlem örnekleminin ilk model değerlendirmesine yetip yetmediğini ölçer.

    Bu fonksiyon eşik değiştirmez ve model optimizasyonu yapmaz. Yalnızca gerçek
    kullanım verisinin ilk ciddi değerlendirme için yeterli olup olmadığını söyler.
    """
    policy = policy or SampleAdequacyPolicy()

    days = max(0, int(observation_days))
    measured = max(0, int(measured_candidate_count))
    mature = max(0, int(mature_20d_candidate_count))
    reliable = max(0, int(reliable_regime_group_count))
    coverage = max(0, int(covered_stage_count))

    conditions = (
        ("Teknik sağlık hazır değil", technical_ready),
        (
            f"En az {policy.minimum_observation_days} gözlem günü gerekli",
            days >= policy.minimum_observation_days,
        ),
        (
            f"En az {policy.minimum_measured_candidates} ölçülmüş aday gerekli",
            measured >= policy.minimum_measured_candidates,
        ),
        (
            f"En az {policy.minimum_mature_20d_candidates} adet 20 günlük olgun sonuç gerekli",
            mature >= policy.minimum_mature_20d_candidates,
        ),
        (
            f"En az {policy.minimum_reliable_regime_groups} güvenilir rejim grubu gerekli",
            reliable >= policy.minimum_reliable_regime_groups,
        ),
        (
            f"E2-E4 için en az {policy.minimum_stage_coverage} aşama kapsaması gerekli",
            coverage >= policy.minimum_stage_coverage,
        ),
    )
    missing = tuple(text for text, ok in conditions if not ok)

    ratios = (
        1.0 if technical_ready else 0.0,
        _ratio(days, policy.minimum_observation_days),
        _ratio(measured, policy.minimum_measured_candidates),
        _ratio(mature, policy.minimum_mature_20d_candidates),
        _ratio(reliable, policy.minimum_reliable_regime_groups),
        _ratio(coverage, policy.minimum_stage_coverage),
    )
    completion_ratio = round(sum(ratios) / len(ratios), 4)
    ready = not missing

    if ready:
        readiness = SampleReadiness.ILK_DEGERLENDIRMEYE_HAZIR
        summary = (
            "İlk gerçek kullanım değerlendirme eşiği karşılandı. "
            "Performans analizi yapılabilir; model eşikleri otomatik değiştirilmez."
        )
    elif technical_ready and completion_ratio >= 0.75:
        readiness = SampleReadiness.ON_DEGERLENDIRME
        summary = (
            "Örneklem ilk değerlendirme eşiğine yaklaştı. Ara sonuçlar izlenebilir "
            "ancak model kararı için veri birikimi sürdürülmeli."
        )
    else:
        readiness = SampleReadiness.IZLEMEYE_DEVAM
        summary = (
            "Canlı örneklem henüz ilk değerlendirme için yeterli değil. "
            "Mevcut V2 modeli değiştirilmeden gözleme devam edilmeli."
        )

    return SampleAdequacyStatus(
        observation_days=days,
        measured_candidate_count=measured,
        mature_20d_candidate_count=mature,
        reliable_regime_group_count=reliable,
        covered_stage_count=coverage,
        readiness=readiness,
        first_evaluation_ready=ready,
        completion_ratio=completion_ratio,
        missing_conditions=missing,
        summary=summary,
    )


def v2_gozlemden_orneklem_yeterliligi(
    observation_status: V2ObservationStatus,
    *,
    mature_20d_candidate_count: int,
    covered_stage_count: int,
    technical_ready: bool = True,
    policy: SampleAdequacyPolicy | None = None,
) -> SampleAdequacyStatus:
    """Sprint-119 canlı gözlem durumunu Sprint-120 yeterlilik kararına taşır."""
    return canli_orneklem_yeterliligini_degerlendir(
        observation_days=observation_status.observation_days,
        measured_candidate_count=observation_status.measured_candidate_count,
        mature_20d_candidate_count=mature_20d_candidate_count,
        reliable_regime_group_count=observation_status.reliable_regime_group_count,
        covered_stage_count=covered_stage_count,
        technical_ready=technical_ready,
        policy=policy,
    )


def orneklem_yeterliligini_metne_cevir(status: SampleAdequacyStatus) -> str:
    missing = "Yok" if not status.missing_conditions else " | ".join(status.missing_conditions)
    return "\n".join(
        [
            "V2 CANLI GÖZLEM - ÖRNEKLEM YETERLİLİĞİ",
            f"Karar: {status.readiness.value}",
            f"İlk değerlendirmeye hazır: {'EVET' if status.first_evaluation_ready else 'HAYIR'}",
            f"Tamamlanma oranı: %{status.completion_ratio * 100:.1f}",
            f"Gözlem günü: {status.observation_days}",
            f"Ölçülmüş aday: {status.measured_candidate_count}",
            f"20 günlük olgun sonuç: {status.mature_20d_candidate_count}",
            f"Güvenilir rejim grubu: {status.reliable_regime_group_count}",
            f"Kapsanan aşama sayısı: {status.covered_stage_count}",
            f"Eksik koşullar: {missing}",
            f"Özet: {status.summary}",
        ]
    )
