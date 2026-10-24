from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JumpCandidateQualityPolicy:
    minimum_technical_score: int = 60
    minimum_volume_ratio: float = 1.0
    minimum_risk_reward: float = 1.5
    maximum_extension_atr: float = 2.0


@dataclass(frozen=True)
class JumpCandidateQualityResult:
    eligible: bool
    technical_ok: bool
    volume_ok: bool
    risk_reward_ok: bool
    entry_ok: bool
    extension_atr: float | None
    reasons: tuple[str, ...]


def _float_attr(obj: object, name: str) -> float | None:
    value = getattr(obj, name, None)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extension_atr(candidate: object) -> float | None:
    close = _float_attr(candidate, "kapanis")
    ema9 = _float_attr(candidate, "ema9")
    atr14 = _float_attr(candidate, "atr14")
    if close is None or ema9 is None or atr14 is None or atr14 <= 0:
        return None
    return max(0.0, (close - ema9) / atr14)


def evaluate_jump_candidate_quality(
    candidate: object,
    *,
    policy: JumpCandidateQualityPolicy | None = None,
) -> JumpCandidateQualityResult:
    """Sıçrama havuzu için açıklanabilir, skor üretmeyen kalite kapısı."""
    policy = policy or JumpCandidateQualityPolicy()
    signal = getattr(candidate, "sinyal", None)
    risk_plan = getattr(candidate, "risk_plani", None)

    technical_score = int(getattr(signal, "skor", 0) or 0)
    technical_view = str(getattr(signal, "karar", "") or "")
    volume_ratio = float(getattr(candidate, "hacim_orani", 0.0) or 0.0)
    risk_reward = float(getattr(risk_plan, "risk_odul_orani", 0.0) or 0.0)
    extension_atr = _extension_atr(candidate)

    technical_ok = (
        technical_score >= policy.minimum_technical_score
        and technical_view != "Negatif Teknik Görünüm"
    )
    volume_ok = volume_ratio >= policy.minimum_volume_ratio
    risk_reward_ok = risk_reward >= policy.minimum_risk_reward
    entry_ok = (
        extension_atr is None
        or extension_atr <= policy.maximum_extension_atr
    )

    reasons: list[str] = []
    reasons.append(
        f"teknik {technical_score} {'uygun' if technical_ok else 'zayıf'}"
    )
    reasons.append(
        f"hacim {volume_ratio:.2f}x {'uygun' if volume_ok else 'zayıf'}"
    )
    reasons.append(
        f"R/R {risk_reward:.2f} {'uygun' if risk_reward_ok else 'zayıf'}"
    )
    if extension_atr is None:
        reasons.append("aşırı uzama ölçümü yok; bloklamadı")
    else:
        reasons.append(
            f"uzama {extension_atr:.2f} ATR "
            f"{'uygun' if entry_ok else 'yüksek'}"
        )

    return JumpCandidateQualityResult(
        eligible=technical_ok and volume_ok and risk_reward_ok and entry_ok,
        technical_ok=technical_ok,
        volume_ok=volume_ok,
        risk_reward_ok=risk_reward_ok,
        entry_ok=entry_ok,
        extension_atr=extension_atr,
        reasons=tuple(reasons),
    )
