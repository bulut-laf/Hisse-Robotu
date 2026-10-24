from __future__ import annotations

from backend.app.prebreakout.prebreakout_models import (
    PreBreakoutFeatures,
    PreBreakoutStage,
)


STAGE_LABELS = {
    PreBreakoutStage.HAZIRLIK_YOK: "Hazırlık yok",
    PreBreakoutStage.E1: "Erken hazırlık",
    PreBreakoutStage.E2: "Dirence yaklaşıyor",
    PreBreakoutStage.E3: "Kırılım adayı",
    PreBreakoutStage.E4: "İlk teyit",
    PreBreakoutStage.HAREKET_BASLAMIS: "Hareket başlamış",
    PreBreakoutStage.REDDEDILDI: "Reddedildi",
}


def asamayi_belirle(
    score: int,
    features: PreBreakoutFeatures,
    *,
    late_entry: bool,
) -> PreBreakoutStage:
    if late_entry:
        return PreBreakoutStage.HAREKET_BASLAMIS
    if score < 45:
        return PreBreakoutStage.HAZIRLIK_YOK
    if score < 60:
        return PreBreakoutStage.E1
    if score < 70:
        return (
            PreBreakoutStage.E2
            if 0.0 <= features.direnc_uzaklik_pct <= 8.0
            else PreBreakoutStage.E1
        )
    if score < 80:
        return (
            PreBreakoutStage.E3
            if 0.0 <= features.direnc_uzaklik_pct <= 5.0
            else PreBreakoutStage.E2
        )
    first_confirmation = (
        features.direnc_uzaklik_pct <= 1.0
        and features.macd_histogram_egimi > 0.0
        and features.hacim_orani_3_10 >= 1.05
    )
    return (
        PreBreakoutStage.E4
        if first_confirmation
        else PreBreakoutStage.E3
    )
