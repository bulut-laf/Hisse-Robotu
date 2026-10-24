from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PreBreakoutStage(StrEnum):
    HAZIRLIK_YOK = "HAZIRLIK_YOK"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"
    HAREKET_BASLAMIS = "HAREKET_BASLAMIS"
    REDDEDILDI = "REDDEDILDI"


@dataclass(frozen=True)
class PreBreakoutConfig:
    minimum_bar: int = 60
    minimum_ortalama_hacim: float = 1_000_000.0
    maksimum_son_gun_getirisi_pct: float = 4.0
    maksimum_uc_gun_getirisi_pct: float = 8.0
    maksimum_ema21_uzakligi_pct: float = 6.0
    maksimum_rsi: float = 72.0
    maksimum_direnc_uzakligi_pct: float = 8.0
    minimum_risk_odul: float = 1.5


@dataclass(frozen=True)
class PreBreakoutFeatures:
    close: float
    ema9: float
    ema21: float
    ema50: float
    rsi14: float
    rsi_egimi: float
    macd: float
    macd_sinyal: float
    macd_histogram: float
    macd_histogram_egimi: float
    atr14: float
    atr_pct: float
    atr_daralma_orani: float
    bes_gun_aralik_daralma_orani: float
    ema9_ema21_mesafe_pct: float
    ema21_uzaklik_pct: float
    ema21_egimi_pct: float
    hacim_orani_3_10: float
    yukselis_hacim_orani: float
    dusus_hacim_orani: float
    direnc: float
    direnc_uzaklik_pct: float
    son_gun_getirisi_pct: float
    uc_gun_getirisi_pct: float
    bes_gun_getirisi_pct: float
    yukselen_dip: bool
    risk_odul: float


@dataclass(frozen=True)
class PreBreakoutScore:
    sikisma: int
    momentum: int
    trend: int
    hacim: int
    direnc: int
    goreceli_guc: int
    risk_odul: int

    @property
    def toplam(self) -> int:
        return (
            self.sikisma
            + self.momentum
            + self.trend
            + self.hacim
            + self.direnc
            + self.goreceli_guc
            + self.risk_odul
        )


@dataclass(frozen=True)
class PreBreakoutResult:
    symbol: str
    score: int
    stage: PreBreakoutStage
    stage_label: str
    features: PreBreakoutFeatures | None
    component_scores: PreBreakoutScore | None
    late_entry: bool
    accepted: bool
    reasons: tuple[str, ...]
    risks: tuple[str, ...]
