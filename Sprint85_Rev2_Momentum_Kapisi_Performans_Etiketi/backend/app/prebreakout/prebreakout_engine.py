from __future__ import annotations

import pandas as pd

from backend.app.prebreakout.prebreakout_features import (
    PreBreakoutDataError,
    ozellikleri_hesapla,
)
from backend.app.prebreakout.prebreakout_filters import (
    gec_giris_riskleri,
    veri_kalitesi_riskleri,
)
from backend.app.prebreakout.prebreakout_models import (
    PreBreakoutConfig,
    PreBreakoutResult,
    PreBreakoutStage,
)
from backend.app.prebreakout.prebreakout_score import skoru_hesapla
from backend.app.prebreakout.prebreakout_stage import (
    STAGE_LABELS,
    asamayi_belirle,
)


def _reasons(features: object, component_scores: object) -> tuple[str, ...]:
    reasons: list[str] = []
    if component_scores.sikisma >= 12:
        reasons.append("Volatilite ve fiyat aralığı daralıyor.")
    if component_scores.momentum >= 12:
        reasons.append("Momentum göstergeleri toparlanıyor.")
    if component_scores.trend >= 12:
        reasons.append("Trend hazırlığı ve yükselen dip yapısı olumlu.")
    if component_scores.hacim >= 8:
        reasons.append("Hacim kontrollü biçimde birikiyor.")
    if component_scores.direnc >= 7:
        reasons.append("Fiyat önemli dirence yakın.")
    if features.risk_odul >= 1.5:
        reasons.append("Erken giriş için risk/ödül kabul edilebilir.")
    return tuple(reasons)


def on_yukselis_hazirligini_analiz_et(
    symbol: str,
    data: pd.DataFrame,
    *,
    config: PreBreakoutConfig | None = None,
    relative_strength_score: int = 5,
) -> PreBreakoutResult:
    active_config = config or PreBreakoutConfig()

    quality_risks = veri_kalitesi_riskleri(data, active_config)
    if quality_risks:
        return PreBreakoutResult(
            symbol=symbol,
            score=0,
            stage=PreBreakoutStage.REDDEDILDI,
            stage_label=STAGE_LABELS[PreBreakoutStage.REDDEDILDI],
            features=None,
            component_scores=None,
            late_entry=False,
            accepted=False,
            reasons=(),
            risks=quality_risks,
        )

    try:
        features = ozellikleri_hesapla(data)
    except PreBreakoutDataError as error:
        return PreBreakoutResult(
            symbol=symbol,
            score=0,
            stage=PreBreakoutStage.REDDEDILDI,
            stage_label=STAGE_LABELS[PreBreakoutStage.REDDEDILDI],
            features=None,
            component_scores=None,
            late_entry=False,
            accepted=False,
            reasons=(),
            risks=(str(error),),
        )

    late_risks = gec_giris_riskleri(features, active_config)
    component_scores = skoru_hesapla(
        features,
        relative_strength_score=relative_strength_score,
    )
    stage = asamayi_belirle(
        component_scores.toplam,
        features,
        late_entry=bool(late_risks),
        momentum_score=component_scores.momentum,
    )

    risks = list(late_risks)
    if features.risk_odul < active_config.minimum_risk_odul:
        risks.append("Risk/ödül minimum koşulun altında.")
    if features.direnc_uzaklik_pct > active_config.maksimum_direnc_uzakligi_pct:
        risks.append("Direnç erken hazırlık için fazla uzakta.")

    accepted = stage in {
        PreBreakoutStage.E1,
        PreBreakoutStage.E2,
        PreBreakoutStage.E3,
        PreBreakoutStage.E4,
    }

    return PreBreakoutResult(
        symbol=symbol,
        score=component_scores.toplam,
        stage=stage,
        stage_label=STAGE_LABELS[stage],
        features=features,
        component_scores=component_scores,
        late_entry=bool(late_risks),
        accepted=accepted,
        reasons=_reasons(features, component_scores),
        risks=tuple(risks),
    )
