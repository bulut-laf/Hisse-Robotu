from __future__ import annotations

import pandas as pd

from backend.app.prebreakout.prebreakout_models import (
    PreBreakoutConfig,
    PreBreakoutFeatures,
)


def veri_kalitesi_riskleri(
    data: pd.DataFrame,
    config: PreBreakoutConfig,
) -> tuple[str, ...]:
    risks: list[str] = []
    if len(data) < config.minimum_bar:
        risks.append("Yetersiz tamamlanmış günlük bar.")
    if "Volume" in data.columns:
        average_volume = float(
            pd.to_numeric(data["Volume"], errors="coerce").tail(20).mean()
        )
        if average_volume < config.minimum_ortalama_hacim:
            risks.append("Ortalama hacim minimum likidite koşulunun altında.")
    return tuple(risks)


def gec_giris_riskleri(
    features: PreBreakoutFeatures,
    config: PreBreakoutConfig,
) -> tuple[str, ...]:
    risks: list[str] = []
    if features.son_gun_getirisi_pct > config.maksimum_son_gun_getirisi_pct:
        risks.append("Son gün primi yüksek; hareket başlamış olabilir.")
    if features.uc_gun_getirisi_pct > config.maksimum_uc_gun_getirisi_pct:
        risks.append("Son üç günlük prim yüksek; geç giriş riski var.")
    if features.ema21_uzaklik_pct > config.maksimum_ema21_uzakligi_pct:
        risks.append("Fiyat EMA21'den aşırı uzaklaşmış.")
    if features.rsi14 > config.maksimum_rsi:
        risks.append("RSI aşırı alım bölgesine yaklaşmış veya geçmiş.")
    if features.direnc_uzaklik_pct < -1.0:
        risks.append("Direnç kırılmış; hareket başlamış olabilir.")
    return tuple(risks)
