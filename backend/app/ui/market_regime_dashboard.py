from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from ..analysis.market_regime import MarketRegimeResult, piyasa_rejimi_karsilastirmasi


@dataclass(frozen=True)
class MarketRegimeContext:
    """Momentum ekranına güvenle aktarılabilen piyasa rejimi bağlamı."""

    rejim: str
    analiz_tarihi: str
    guven_duzeyi: str
    kaynak: str
    veri_durumu: str
    beklenen_tarih: str
    olusturulma_tarihi: str
    gecerli: bool
    gecersizlik_nedeni: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "rejim": self.rejim,
            "analiz_tarihi": self.analiz_tarihi,
            "guven_duzeyi": self.guven_duzeyi,
            "kaynak": self.kaynak,
            "veri_durumu": self.veri_durumu,
            "beklenen_tarih": self.beklenen_tarih,
            "olusturulma_tarihi": self.olusturulma_tarihi,
            "gecerli": self.gecerli,
            "gecersizlik_nedeni": self.gecersizlik_nedeni,
        }


@dataclass(frozen=True)
class MarketRegimeDashboardResult:
    sonuclar: tuple[MarketRegimeResult, ...]

    @property
    def ana_rejim(self) -> MarketRegimeResult:
        return next(item for item in self.sonuclar if item.sembol == "XU100")

    @property
    def eksik_endeksler(self) -> tuple[str, ...]:
        mevcut = {item.sembol for item in self.sonuclar}
        return tuple(
            kod for kod in ("XU100", "XU030", "XUTUM")
            if kod not in mevcut
        )

    @property
    def veri_durumlari(self) -> tuple[dict[str, str], ...]:
        return tuple(
            {
                "sembol": item.sembol,
                "kaynak": item.yahoo_sembolu,
                "son_tarih": str(item.analiz_tarihi.date()),
                "durum": (
                    "Güncel"
                    if not item.veri_tazeligi.kilitli
                    else "Kilitli"
                ),
                "guven": item.guven_duzeyi,
            }
            for item in self.sonuclar
        )


def piyasa_rejimi_baglami_olustur(
    sonuc: MarketRegimeDashboardResult,
    *,
    bugun: date | None = None,
) -> MarketRegimeContext:
    """Ana BIST 100 sonucundan tarihli ve doğrulanabilir rejim bağlamı üretir."""

    ana = sonuc.ana_rejim
    bugun_degeri = bugun or date.today()
    veri_guncel = not ana.veri_tazeligi.kilitli
    guven_var = bool(str(ana.guven_duzeyi).strip())
    gecerli = veri_guncel and guven_var

    nedenler: list[str] = []
    if not veri_guncel:
        nedenler.append(
            "BIST 100 rejim verisi tazelik kilidinde."
        )
    if not guven_var:
        nedenler.append(
            "Piyasa rejimi güven düzeyi üretilemedi."
        )

    return MarketRegimeContext(
        rejim=ana.rejim,
        analiz_tarihi=str(ana.analiz_tarihi),
        guven_duzeyi=str(ana.guven_duzeyi),
        kaynak=str(ana.yahoo_sembolu),
        veri_durumu="Güncel" if veri_guncel else "Kilitli",
        beklenen_tarih=str(ana.veri_tazeligi.beklenen_tarih),
        olusturulma_tarihi=bugun_degeri.isoformat(),
        gecerli=gecerli,
        gecersizlik_nedeni=" ".join(nedenler),
    )



class MarketRegimeDashboardError(Exception):
    """Piyasa rejimi ekranı hazırlanamadığında kullanılır."""


RegimeLoader = Callable[..., tuple[MarketRegimeResult, ...]]


class MarketRegimeDashboardService:
    def __init__(self, yukleyici: RegimeLoader = piyasa_rejimi_karsilastirmasi) -> None:
        self._yukleyici = yukleyici

    def calistir(self) -> MarketRegimeDashboardResult:
        try:
            sonuclar = tuple(self._yukleyici())
        except Exception as hata:
            raise MarketRegimeDashboardError(str(hata)) from hata
        if not sonuclar or not any(item.sembol == "XU100" for item in sonuclar):
            raise MarketRegimeDashboardError("BIST 100 piyasa rejimi sonucu üretilemedi.")
        return MarketRegimeDashboardResult(sonuclar=sonuclar)
