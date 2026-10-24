from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

import pandas as pd

from ..data.multi_timeframe_data import (
    GUNLUK,
    HAFTALIK,
    SAATLIK,
    MultiTimeframeDataBundle,
    TimeframeSnapshot,
)
from ..indicators.technical_indicators import (
    IndicatorError,
    teknik_gostergeleri_ekle,
)


POZITIF = "Pozitif"
NOTR = "Nötr"
NEGATIF = "Negatif"

GUCLU_POZITIF_UYUM = "Güçlü Pozitif Uyum"
POZITIF_SAATLIK_TEYIT_BEKLENIYOR = (
    "Pozitif Uyum — Saatlik Teyit Bekleniyor"
)
GUCLU_NEGATIF_UYUM = "Güçlü Negatif Uyum"
NEGATIF_SAATLIK_TEYIT_BEKLENIYOR = (
    "Negatif Uyum — Saatlik Teyit Bekleniyor"
)
TREND_GUNLUK_CELISKILI = "Haftalık Trend ile Günlük Teyit Çelişkili"
TEPKI_YUKSELISI_RISKI = "Ana Trende Karşı Tepki Yükselişi Riski"
ZAMAN_DILIMLERI_UYUMSUZ = "Zaman Dilimleri Uyumsuz"


class MultiTimeframeAnalysisError(Exception):
    """Çoklu zaman dilimi teknik analizi üretilemediğinde kullanılır."""


@dataclass(frozen=True)
class TimeframeTechnicalResult:
    """Tek zaman diliminin son tamamlanmış mumuna ait teknik özeti."""

    ad: str
    interval: str
    son_zaman: pd.Timestamp
    kapanis: float
    ema9: float
    ema21: float
    rsi14: float
    macd: float
    macd_sinyal: float
    macd_histogram: float
    skor: int
    yon: str
    pozitif_nedenler: tuple[str, ...]
    riskler: tuple[str, ...]


@dataclass(frozen=True)
class MultiTimeframeTechnicalAnalysis:
    """Haftalık trend, günlük teyit ve saatlik zamanlama özeti."""

    sembol: str
    veri_kimligi: str
    analiz_kimligi: str
    haftalik: TimeframeTechnicalResult
    gunluk: TimeframeTechnicalResult
    saatlik: TimeframeTechnicalResult
    uyum_skoru: int
    teyit_durumu: str
    pozitif_nedenler: tuple[str, ...]
    riskler: tuple[str, ...]

    def getir(self, ad: str) -> TimeframeTechnicalResult:
        aranan = ad.strip().casefold()
        sonuclar = (self.haftalik, self.gunluk, self.saatlik)

        for sonuc in sonuclar:
            if sonuc.ad.casefold() == aranan:
                return sonuc

        raise KeyError(f"Zaman dilimi analiz sonucu bulunamadı: {ad}")


_GOSTERGE_SUTUNLARI = (
    "Close",
    "EMA9",
    "EMA21",
    "RSI14",
    "MACD",
    "MACD_Sinyal",
    "MACD_Histogram",
)


def coklu_zaman_dilimi_teknik_analizi_yap(
    paket: MultiTimeframeDataBundle,
) -> MultiTimeframeTechnicalAnalysis:
    """
    Tamamlanmış saatlik, günlük ve haftalık veriyi bağımsız analiz eder.

    Haftalık veri ana trendi, günlük veri yön teyidini, saatlik veri ise
    kısa vadeli zamanlamayı temsil eder. Bu katman alış/satış fiyatı veya
    pozisyon emri üretmez; yalnızca zaman dilimleri arasındaki teknik uyumu
    açıklar.
    """
    snapshots = _zorunlu_zaman_dilimlerini_getir(paket)

    haftalik = _zaman_dilimini_analiz_et(snapshots[HAFTALIK])
    gunluk = _zaman_dilimini_analiz_et(snapshots[GUNLUK])
    saatlik = _zaman_dilimini_analiz_et(snapshots[SAATLIK])

    uyum_skoru = round(
        haftalik.skor * 0.45
        + gunluk.skor * 0.35
        + saatlik.skor * 0.20
    )
    teyit_durumu = _teyit_durumunu_belirle(
        haftalik=haftalik,
        gunluk=gunluk,
        saatlik=saatlik,
    )
    pozitif_nedenler, riskler = _ortak_aciklamalari_olustur(
        haftalik=haftalik,
        gunluk=gunluk,
        saatlik=saatlik,
        teyit_durumu=teyit_durumu,
    )
    analiz_kimligi = _analiz_kimligi_uret(
        paket=paket,
        haftalik=haftalik,
        gunluk=gunluk,
        saatlik=saatlik,
    )

    return MultiTimeframeTechnicalAnalysis(
        sembol=paket.sembol,
        veri_kimligi=paket.veri_kimligi,
        analiz_kimligi=analiz_kimligi,
        haftalik=haftalik,
        gunluk=gunluk,
        saatlik=saatlik,
        uyum_skoru=int(uyum_skoru),
        teyit_durumu=teyit_durumu,
        pozitif_nedenler=pozitif_nedenler,
        riskler=riskler,
    )


def _zorunlu_zaman_dilimlerini_getir(
    paket: MultiTimeframeDataBundle,
) -> dict[str, TimeframeSnapshot]:
    snapshots: dict[str, TimeframeSnapshot] = {}

    for snapshot in paket.zaman_dilimleri:
        if snapshot.ad in {SAATLIK, GUNLUK, HAFTALIK}:
            if snapshot.ad in snapshots:
                raise MultiTimeframeAnalysisError(
                    f"Yinelenen zaman dilimi bulundu: {snapshot.ad}"
                )
            snapshots[snapshot.ad] = snapshot

    eksikler = [
        ad for ad in (HAFTALIK, GUNLUK, SAATLIK)
        if ad not in snapshots
    ]
    if eksikler:
        raise MultiTimeframeAnalysisError(
            "Teknik analiz için eksik zaman dilimleri: "
            + ", ".join(eksikler)
        )

    return snapshots


def _zaman_dilimini_analiz_et(
    snapshot: TimeframeSnapshot,
) -> TimeframeTechnicalResult:
    try:
        gostergeli = teknik_gostergeleri_ekle(snapshot.veri)
    except (IndicatorError, ValueError) as hata:
        raise MultiTimeframeAnalysisError(
            f"{snapshot.ad} göstergeleri hesaplanamadı: {hata}"
        ) from hata

    gecerli = gostergeli.dropna(subset=list(_GOSTERGE_SUTUNLARI))
    if len(gecerli) < 2:
        raise MultiTimeframeAnalysisError(
            f"{snapshot.ad} teknik analizi için en az iki geçerli "
            "gösterge satırı gereklidir."
        )

    son = gecerli.iloc[-1]
    onceki = gecerli.iloc[-2]
    pozitif_nedenler: list[str] = []
    riskler: list[str] = []
    skor = 0

    if float(son["Close"]) > float(son["EMA21"]):
        skor += 20
        pozitif_nedenler.append("Kapanış EMA21 üzerinde.")
    else:
        riskler.append("Kapanış EMA21 altında.")

    if float(son["EMA9"]) > float(son["EMA21"]):
        skor += 20
        pozitif_nedenler.append("EMA9, EMA21 üzerinde.")
    else:
        riskler.append("EMA9, EMA21 altında.")

    rsi = float(son["RSI14"])
    if 50.0 <= rsi <= 68.0:
        skor += 20
        pozitif_nedenler.append("RSI sağlıklı pozitif bölgede.")
    elif 45.0 <= rsi < 50.0:
        skor += 10
        pozitif_nedenler.append("RSI nötr bölgeye yakın.")
    elif 68.0 < rsi <= 75.0:
        skor += 10
        riskler.append("RSI güçlü fakat aşırı alıma yaklaşıyor.")
    elif rsi > 75.0:
        riskler.append("RSI aşırı alım bölgesinde.")
    elif rsi < 35.0:
        riskler.append("RSI belirgin zayıflık bölgesinde.")
    else:
        riskler.append("RSI pozitif teyit vermiyor.")

    if float(son["MACD"]) > float(son["MACD_Sinyal"]):
        skor += 20
        pozitif_nedenler.append("MACD, sinyal çizgisinin üzerinde.")
    else:
        riskler.append("MACD, sinyal çizgisinin altında.")

    if float(son["MACD_Histogram"]) > float(onceki["MACD_Histogram"]):
        skor += 20
        pozitif_nedenler.append("MACD histogramı güçleniyor.")
    else:
        riskler.append("MACD histogramı güç kaybediyor.")

    yon = _yon_belirle(skor)

    return TimeframeTechnicalResult(
        ad=snapshot.ad,
        interval=snapshot.interval,
        son_zaman=pd.Timestamp(gecerli.index[-1]),
        kapanis=float(son["Close"]),
        ema9=float(son["EMA9"]),
        ema21=float(son["EMA21"]),
        rsi14=rsi,
        macd=float(son["MACD"]),
        macd_sinyal=float(son["MACD_Sinyal"]),
        macd_histogram=float(son["MACD_Histogram"]),
        skor=int(skor),
        yon=yon,
        pozitif_nedenler=tuple(pozitif_nedenler),
        riskler=tuple(riskler),
    )


def _yon_belirle(skor: int) -> str:
    if skor >= 70:
        return POZITIF
    if skor >= 40:
        return NOTR
    return NEGATIF


def _teyit_durumunu_belirle(
    haftalik: TimeframeTechnicalResult,
    gunluk: TimeframeTechnicalResult,
    saatlik: TimeframeTechnicalResult,
) -> str:
    if haftalik.yon == POZITIF and gunluk.yon == POZITIF:
        if saatlik.yon == POZITIF:
            return GUCLU_POZITIF_UYUM
        return POZITIF_SAATLIK_TEYIT_BEKLENIYOR

    if haftalik.yon == NEGATIF and gunluk.yon == NEGATIF:
        if saatlik.yon == NEGATIF:
            return GUCLU_NEGATIF_UYUM
        return NEGATIF_SAATLIK_TEYIT_BEKLENIYOR

    if haftalik.yon == POZITIF and gunluk.yon == NEGATIF:
        return TREND_GUNLUK_CELISKILI

    if haftalik.yon == NEGATIF and gunluk.yon == POZITIF:
        return TEPKI_YUKSELISI_RISKI

    return ZAMAN_DILIMLERI_UYUMSUZ


def _ortak_aciklamalari_olustur(
    haftalik: TimeframeTechnicalResult,
    gunluk: TimeframeTechnicalResult,
    saatlik: TimeframeTechnicalResult,
    teyit_durumu: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    pozitif_nedenler: list[str] = []
    riskler: list[str] = []

    if haftalik.yon == POZITIF:
        pozitif_nedenler.append("Haftalık ana trend pozitif.")
    elif haftalik.yon == NEGATIF:
        riskler.append("Haftalık ana trend negatif.")
    else:
        riskler.append("Haftalık ana trend henüz net değil.")

    if gunluk.yon == POZITIF:
        pozitif_nedenler.append("Günlük yön haftalık görünümü destekliyor.")
    elif gunluk.yon == NEGATIF:
        riskler.append("Günlük yön aşağı baskı gösteriyor.")
    else:
        riskler.append("Günlük yön teyidi nötr.")

    if saatlik.yon == POZITIF:
        pozitif_nedenler.append("Saatlik zamanlama pozitif.")
    elif saatlik.yon == NEGATIF:
        riskler.append("Saatlik zamanlama negatif.")
    else:
        riskler.append("Saatlik zamanlama teyit vermiyor.")

    if teyit_durumu == GUCLU_POZITIF_UYUM:
        pozitif_nedenler.append("Üç zaman dilimi aynı pozitif yönde.")
    elif teyit_durumu == GUCLU_NEGATIF_UYUM:
        riskler.append("Üç zaman dilimi aynı negatif yönde.")
    elif teyit_durumu in {
        TREND_GUNLUK_CELISKILI,
        TEPKI_YUKSELISI_RISKI,
        ZAMAN_DILIMLERI_UYUMSUZ,
    }:
        riskler.append("Zaman dilimleri arasında yön uyuşmazlığı var.")

    return tuple(pozitif_nedenler), tuple(riskler)


def _analiz_kimligi_uret(
    paket: MultiTimeframeDataBundle,
    haftalik: TimeframeTechnicalResult,
    gunluk: TimeframeTechnicalResult,
    saatlik: TimeframeTechnicalResult,
) -> str:
    icerik = "|".join(
        (
            paket.sembol,
            paket.veri_kimligi,
            f"{haftalik.skor}:{haftalik.yon}",
            f"{gunluk.skor}:{gunluk.yon}",
            f"{saatlik.skor}:{saatlik.yon}",
        )
    ).encode("utf-8")
    return sha256(icerik).hexdigest()[:12]
