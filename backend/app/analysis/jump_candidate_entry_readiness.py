from __future__ import annotations

from dataclasses import dataclass

from backend.app.analysis.jump_candidate_quality import (
    JumpCandidateQualityPolicy,
    evaluate_jump_candidate_quality,
)


READY = "GİRİŞE HAZIR"
WAIT_CONFIRMATION = "TEYİT BEKLİYOR"
EARLY = "ERKEN"
OVEREXTENDED = "AŞIRI UZAMIŞ"


@dataclass(frozen=True)
class JumpCandidateEntryReadinessPolicy:
    minimum_ready_technical_score: int = 70
    minimum_ready_volume_ratio: float = 1.20
    minimum_ready_risk_reward: float = 1.50
    maximum_ready_extension_atr: float = 1.25
    maximum_wait_extension_atr: float = 2.00


@dataclass(frozen=True)
class JumpCandidateEntryReadinessResult:
    state: str
    ready: bool
    technical_score: int
    volume_ratio: float
    risk_reward: float
    extension_atr: float | None
    resistance_distance_pct: float | None
    reasons: tuple[str, ...]


def _float_attr(obj: object, name: str) -> float | None:
    value = getattr(obj, name, None)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resistance_distance_pct(candidate: object) -> float | None:
    levels = getattr(candidate, "destek_direnc", None)
    return _float_attr(levels, "direnc_uzaklik_yuzde") if levels is not None else None


def evaluate_jump_candidate_entry_readiness(
    candidate: object,
    *,
    policy: JumpCandidateEntryReadinessPolicy | None = None,
) -> JumpCandidateEntryReadinessResult:
    """Sıçrama adayının giriş zamanlamasını açıklanabilir durumlara ayırır.

    Yeni skor üretmez. Mevcut teknik skor, hacim, risk/ödül ve EMA9-ATR
    uzama kanıtlarını kullanır. Destek/direnç mesafesi yalnız açıklayıcı bağlamdır.
    """
    policy = policy or JumpCandidateEntryReadinessPolicy()
    signal = getattr(candidate, "sinyal", None)
    risk_plan = getattr(candidate, "risk_plani", None)

    technical_score = int(getattr(signal, "skor", 0) or 0)
    technical_view = str(getattr(signal, "karar", "") or "")
    volume_ratio = float(getattr(candidate, "hacim_orani", 0.0) or 0.0)
    risk_reward = float(getattr(risk_plan, "risk_odul_orani", 0.0) or 0.0)
    resistance_distance_pct = _resistance_distance_pct(candidate)

    quality = evaluate_jump_candidate_quality(
        candidate,
        policy=JumpCandidateQualityPolicy(
            minimum_technical_score=60,
            minimum_volume_ratio=1.0,
            minimum_risk_reward=policy.minimum_ready_risk_reward,
            maximum_extension_atr=policy.maximum_wait_extension_atr,
        ),
    )
    extension_atr = quality.extension_atr

    reasons: list[str] = []

    if extension_atr is not None and extension_atr > policy.maximum_wait_extension_atr:
        state = OVEREXTENDED
        reasons.append(
            f"EMA9 üzeri uzama {extension_atr:.2f} ATR; "
            f"{policy.maximum_wait_extension_atr:.2f} ATR sınırının üzerinde."
        )
    elif not quality.eligible:
        state = EARLY
        if technical_score < 60 or technical_view == "Negatif Teknik Görünüm":
            reasons.append("Teknik kalite sıçrama giriş hazırlığı için henüz yeterli değil.")
        if volume_ratio < 1.0:
            reasons.append("Hacim teyidi henüz oluşmadı.")
        if risk_reward < policy.minimum_ready_risk_reward:
            reasons.append("Risk/getiri giriş hazırlığı için yetersiz.")
        if not reasons:
            reasons.append("Kalite kapısı henüz tamamlanmadı.")
    else:
        strong_technical = (
            technical_score >= policy.minimum_ready_technical_score
            and technical_view == "Pozitif Teknik Görünüm"
        )
        strong_volume = volume_ratio >= policy.minimum_ready_volume_ratio
        acceptable_extension = (
            extension_atr is None
            or extension_atr <= policy.maximum_ready_extension_atr
        )

        if strong_technical and strong_volume and acceptable_extension:
            state = READY
            reasons.append(
                f"Teknik {technical_score}, hacim {volume_ratio:.2f}x ve "
                f"R/R {risk_reward:.2f} giriş hazırlığını destekliyor."
            )
        else:
            state = WAIT_CONFIRMATION
            if not strong_technical:
                reasons.append(
                    f"Teknik skor/görünüm henüz güçlü teyit vermiyor ({technical_score})."
                )
            if not strong_volume:
                reasons.append(
                    f"Hacim {volume_ratio:.2f}x; güçlü giriş teyidi için "
                    f"{policy.minimum_ready_volume_ratio:.2f}x bekleniyor."
                )
            if not acceptable_extension and extension_atr is not None:
                reasons.append(
                    f"Uzama {extension_atr:.2f} ATR; fiyatın giriş bölgesine "
                    "yaklaşması bekleniyor."
                )

    if resistance_distance_pct is not None:
        reasons.append(
            f"En yakın direnç mesafesi %{resistance_distance_pct:.2f}; "
            "yalnız zamanlama bağlamı olarak gösteriliyor."
        )

    if extension_atr is None:
        reasons.append("ATR uzama ölçümü yok; tek başına giriş durumunu bloklamadı.")

    return JumpCandidateEntryReadinessResult(
        state=state,
        ready=state == READY,
        technical_score=technical_score,
        volume_ratio=volume_ratio,
        risk_reward=risk_reward,
        extension_atr=extension_atr,
        resistance_distance_pct=resistance_distance_pct,
        reasons=tuple(reasons),
    )
