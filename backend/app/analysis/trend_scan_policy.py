from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


REJIM_POZITIF = "Pozitif"
REJIM_SECICI = "Seçici"
REJIM_RISKLI = "Riskli"


class TrendCandidateLike(Protocol):
    momentum_skoru: int
    trend_puani: int
    yirmi_gunluk_zirve_uzakligi: float
    kirilim: bool
    sinif: str


@dataclass(frozen=True)
class TrendScanPolicy:
    rejim: str
    minimum_momentum_skoru: int
    minimum_trend_puani: int
    azami_direnc_uzakligi: float
    kirilim_veya_yuksek_hazirlik_zorunlu: bool = False

    def __post_init__(self) -> None:
        if self.rejim not in (REJIM_POZITIF, REJIM_SECICI, REJIM_RISKLI):
            raise ValueError(f"Desteklenmeyen piyasa rejimi: {self.rejim}")
        if not 0 <= self.minimum_momentum_skoru <= 100:
            raise ValueError("Minimum momentum skoru 0 ile 100 arasında olmalıdır.")
        if not 0 <= self.minimum_trend_puani <= 15:
            raise ValueError("Minimum trend puanı 0 ile 15 arasında olmalıdır.")
        if not 0.0 <= self.azami_direnc_uzakligi <= 1.0:
            raise ValueError("Azami direnç uzaklığı 0 ile 1 arasında olmalıdır.")


@dataclass(frozen=True)
class TrendScanDecision:
    uygun: bool
    rejim: str
    nedenler: tuple[str, ...]


def rejime_gore_trend_politikasi(rejim: str) -> TrendScanPolicy:
    if rejim == REJIM_POZITIF:
        return TrendScanPolicy(
            rejim=rejim,
            minimum_momentum_skoru=55,
            minimum_trend_puani=8,
            azami_direnc_uzakligi=0.05,
        )
    if rejim == REJIM_SECICI:
        return TrendScanPolicy(
            rejim=rejim,
            minimum_momentum_skoru=65,
            minimum_trend_puani=10,
            azami_direnc_uzakligi=0.03,
        )
    if rejim == REJIM_RISKLI:
        return TrendScanPolicy(
            rejim=rejim,
            minimum_momentum_skoru=75,
            minimum_trend_puani=12,
            azami_direnc_uzakligi=0.02,
            kirilim_veya_yuksek_hazirlik_zorunlu=True,
        )
    raise ValueError(f"Desteklenmeyen piyasa rejimi: {rejim}")


def trend_adayini_degerlendir(
    aday: TrendCandidateLike,
    politika: TrendScanPolicy,
) -> TrendScanDecision:
    nedenler: list[str] = []

    if aday.momentum_skoru < politika.minimum_momentum_skoru:
        nedenler.append(
            f"Momentum skoru {aday.momentum_skoru}; "
            f"gerekli en az {politika.minimum_momentum_skoru}."
        )

    if aday.trend_puani < politika.minimum_trend_puani:
        nedenler.append(
            f"Trend puanı {aday.trend_puani}/15; "
            f"gerekli en az {politika.minimum_trend_puani}/15."
        )

    if aday.yirmi_gunluk_zirve_uzakligi > politika.azami_direnc_uzakligi:
        nedenler.append(
            "20 günlük dirence uzaklık "
            f"%{aday.yirmi_gunluk_zirve_uzakligi * 100:.2f}; "
            f"izin verilen en fazla %{politika.azami_direnc_uzakligi * 100:.2f}."
        )

    if politika.kirilim_veya_yuksek_hazirlik_zorunlu:
        yuksek_hazirlik = (
            aday.sinif.startswith("B ")
            or aday.sinif.startswith("C ")
            or aday.sinif.startswith("E3 ")
        )
        if not aday.kirilim and not yuksek_hazirlik:
            nedenler.append(
                "Riskli rejimde kırılım veya yüksek hazırlık sınıfı zorunludur."
            )

    return TrendScanDecision(
        uygun=not nedenler,
        rejim=politika.rejim,
        nedenler=tuple(nedenler),
    )
