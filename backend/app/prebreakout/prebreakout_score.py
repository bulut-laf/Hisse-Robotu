from __future__ import annotations

from backend.app.prebreakout.prebreakout_models import (
    PreBreakoutFeatures,
    PreBreakoutScore,
)


def _clamp(value: int, maximum: int) -> int:
    return max(0, min(maximum, value))


def skoru_hesapla(
    features: PreBreakoutFeatures,
    *,
    relative_strength_score: int = 5,
) -> PreBreakoutScore:
    contraction = 0
    if features.atr_daralma_orani <= 0.85:
        contraction += 10
    elif features.atr_daralma_orani <= 1.0:
        contraction += 6
    if features.bes_gun_aralik_daralma_orani <= 0.80:
        contraction += 10
    elif features.bes_gun_aralik_daralma_orani <= 1.0:
        contraction += 6

    momentum = 0
    if 45.0 <= features.rsi14 <= 60.0:
        momentum += 8
    elif 40.0 <= features.rsi14 <= 65.0:
        momentum += 5
    if features.rsi_egimi > 0:
        momentum += 5
    if features.macd_histogram_egimi > 0:
        momentum += 5
    if features.macd_histogram <= 0.0 and features.macd_histogram_egimi > 0:
        momentum += 2

    trend = 0
    if -2.0 <= features.ema21_uzaklik_pct <= 3.0:
        trend += 7
    elif -4.0 <= features.ema21_uzaklik_pct <= 5.0:
        trend += 4
    if abs(features.ema9_ema21_mesafe_pct) <= 1.5:
        trend += 5
    elif abs(features.ema9_ema21_mesafe_pct) <= 3.0:
        trend += 3
    if features.ema21_egimi_pct > 0:
        trend += 4
    if features.yukselen_dip:
        trend += 4

    volume = 0
    if 1.05 <= features.hacim_orani_3_10 <= 1.50:
        volume += 8
    elif 0.90 <= features.hacim_orani_3_10 < 1.05:
        volume += 5
    elif 1.50 < features.hacim_orani_3_10 <= 2.00:
        volume += 4
    if features.yukselis_hacim_orani > features.dusus_hacim_orani:
        volume += 7

    resistance = 0
    if 0.0 <= features.direnc_uzaklik_pct <= 3.0:
        resistance = 10
    elif 3.0 < features.direnc_uzaklik_pct <= 5.0:
        resistance = 7
    elif 5.0 < features.direnc_uzaklik_pct <= 8.0:
        resistance = 4

    risk_reward = 0
    if features.risk_odul >= 2.0:
        risk_reward = 5
    elif features.risk_odul >= 1.5:
        risk_reward = 3

    return PreBreakoutScore(
        sikisma=_clamp(contraction, 20),
        momentum=_clamp(momentum, 20),
        trend=_clamp(trend, 20),
        hacim=_clamp(volume, 15),
        direnc=_clamp(resistance, 10),
        goreceli_guc=_clamp(relative_strength_score, 10),
        risk_odul=_clamp(risk_reward, 5),
    )
