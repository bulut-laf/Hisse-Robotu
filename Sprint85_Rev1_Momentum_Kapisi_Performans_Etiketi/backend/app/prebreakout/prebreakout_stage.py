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
    momentum_score: int | None = None,
) -> PreBreakoutStage:
    """
    Toplam skorun yanında zorunlu momentum kapısını uygular.

    E2-E4 aşamaları yalnızca aktif momentum toparlanması varsa üretilebilir.
    Negatif MACD histogram eğimi olan adaylar toplam skorları yüksek olsa bile
    en fazla E1 seviyesinde kalır. E3-E4 için RSI eğimi de pozitif olmalıdır.
    """
    if late_entry:
        return PreBreakoutStage.HAREKET_BASLAMIS
    if score < 45:
        return PreBreakoutStage.HAZIRLIK_YOK
    if score < 60:
        return PreBreakoutStage.E1

    momentum_yeterli = (
        momentum_score is None or momentum_score >= 10
    )
    macd_toparlaniyor = features.macd_histogram_egimi > 0.0

    if not momentum_yeterli or not macd_toparlaniyor:
        return PreBreakoutStage.E1

    if score < 70:
        return (
            PreBreakoutStage.E2
            if 0.0 <= features.direnc_uzaklik_pct <= 8.0
            else PreBreakoutStage.E1
        )

    rsi_toparlaniyor = features.rsi_egimi > 0.0

    if score < 80:
        return (
            PreBreakoutStage.E3
            if (
                rsi_toparlaniyor
                and 0.0 <= features.direnc_uzaklik_pct <= 5.0
            )
            else PreBreakoutStage.E2
        )

    first_confirmation = (
        rsi_toparlaniyor
        and features.direnc_uzaklik_pct <= 1.0
        and features.hacim_orani_3_10 >= 1.05
    )
    return (
        PreBreakoutStage.E4
        if first_confirmation
        else PreBreakoutStage.E3
    )
