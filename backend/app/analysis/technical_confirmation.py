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
    ema,
    teknik_gostergeleri_ekle,
)
from .support_resistance import (
    SupportResistanceError,
    destek_direnc_bul,
)


POZITIF = "Pozitif"
NOTR = "Nötr"
NEGATIF = "Negatif"

TEYITLI_YUKARI_KIRILIM = "Teyitli Yukarı Kırılım"
ERKEN_YUKARI_UYARI = "Erken Yukarı Kırılım Uyarısı"
TEYITLI_ASAGI_KIRILIM = "Teyitli Aşağı Kırılım"
ERKEN_ASAGI_UYARI = "Erken Aşağı Kırılım Uyarısı"
KIRILIM_YOK = "Güncel Kırılım Yok"
TREND_CIZGISI_YOK = "Yeterli Trend Çizgisi Yok"

EMA_POZITIF_KESISIM = "Pozitif EMA Kesişimi"
EMA_NEGATIF_KESISIM = "Negatif EMA Kesişimi"
EMA_POZITIF_YAPI = "Pozitif EMA Yapısı"
EMA_NEGATIF_YAPI = "Negatif EMA Yapısı"
EMA_ESIT = "EMA Değerleri Eşit"

GOLDEN_CROSS = "Golden Cross"
DEATH_CROSS = "Death Cross"
UZUN_VADE_POZITIF = "SMA50, SMA200 Üzerinde"
UZUN_VADE_NEGATIF = "SMA50, SMA200 Altında"
UZUN_VADE_ESIT = "SMA50 ve SMA200 Eşit"
UZUN_VADE_YETERSIZ = "SMA200 Geçmişi Yetersiz"

POZITIF_TEKNIK_TEYIT = "Pozitif Teknik Teyit"
NEGATIF_TEKNIK_TEYIT = "Negatif Teknik Teyit"
CELISKILI_TEKNIK_GORUNUM = "Çelişkili Teknik Görünüm"
TEYIT_BEKLENIYOR = "Teknik Teyit Bekleniyor"


class TechnicalConfirmationError(Exception):
    """Trend, kırılım ve teknik teyit analizi üretilemediğinde kullanılır."""


@dataclass(frozen=True)
class TrendlineBreakoutResult:
    """Son tamamlanmış mumdaki trend çizgisi kırılımını açıklar."""

    durum: str
    yon: str
    cizgi_tipi: str
    cizgi_degeri: float | None
    onceki_cizgi_degeri: float | None
    pivot_sayisi: int
    kapanis_teyidi: bool
    erken_uyari: bool
    hacim_orani: float | None
    hacim_teyidi: bool


@dataclass(frozen=True)
class MovingAverageConfirmation:
    """Kısa, orta ve uzun vadeli hareketli ortalama teyitleri."""

    ema9: float
    ema21: float
    ema55: float
    sma50: float
    sma200: float
    ema9_21_durumu: str
    ema21_55_durumu: str
    uzun_vade_durumu: str
    golden_cross: bool
    death_cross: bool


@dataclass(frozen=True)
class MomentumConfirmation:
    """RSI ve MACD'nin ortak momentum teyidi."""

    rsi14: float
    macd: float
    macd_sinyal: float
    macd_histogram: float
    histogram_gucleniyor: bool
    durum: str


@dataclass(frozen=True)
class TimeframeConfirmationResult:
    """Tek zaman diliminin teknik teyit özeti."""

    ad: str
    interval: str
    son_zaman: pd.Timestamp
    kapanis: float
    destek: float | None
    direnc: float | None
    destek_gucu: str | None
    direnc_gucu: str | None
    kirilim: TrendlineBreakoutResult
    ortalamalar: MovingAverageConfirmation
    momentum: MomentumConfirmation
    skor: int
    yon: str
    pozitif_nedenler: tuple[str, ...]
    riskler: tuple[str, ...]


@dataclass(frozen=True)
class MultiTimeframeTechnicalConfirmation:
    """Haftalık, günlük ve saatlik teknik teyitlerin ortak sonucu."""

    sembol: str
    veri_kimligi: str
    analiz_kimligi: str
    haftalik: TimeframeConfirmationResult
    gunluk: TimeframeConfirmationResult
    saatlik: TimeframeConfirmationResult
    teyit_skoru: int
    teyit_durumu: str
    pozitif_nedenler: tuple[str, ...]
    riskler: tuple[str, ...]

    def getir(self, ad: str) -> TimeframeConfirmationResult:
        aranan = ad.strip().casefold()
        for sonuc in (self.haftalik, self.gunluk, self.saatlik):
            if sonuc.ad.casefold() == aranan:
                return sonuc
        raise KeyError(f"Zaman dilimi teknik teyidi bulunamadı: {ad}")


@dataclass(frozen=True)
class _Pivot:
    konum: int
    fiyat: float


@dataclass(frozen=True)
class _TrendLine:
    tip: str
    ilk: _Pivot
    son: _Pivot

    def deger(self, konum: int) -> float:
        egim = (self.son.fiyat - self.ilk.fiyat) / (
            self.son.konum - self.ilk.konum
        )
        return self.ilk.fiyat + egim * (konum - self.ilk.konum)


_GOSTERGE_SUTUNLARI = (
    "Close",
    "EMA9",
    "EMA21",
    "EMA55",
    "SMA50",
    "SMA200",
    "RSI14",
    "MACD",
    "MACD_Sinyal",
    "MACD_Histogram",
    "Hacim_Orani_20",
)


def teknik_teyit_analizi_yap(
    paket: MultiTimeframeDataBundle,
) -> MultiTimeframeTechnicalConfirmation:
    """
    Tamamlanmış haftalık, günlük ve saatlik mumlarda teknik teyit üretir.

    Bu katman trend çizgisi kırılımını, hacim teyidini, EMA kesişimlerini,
    Golden Cross / Death Cross durumunu ve RSI-MACD momentumunu hesaplar.
    Henüz alış, satış, stop veya hedef fiyatı üretmez.
    """
    snapshots = _zorunlu_zaman_dilimlerini_getir(paket)

    haftalik = zaman_dilimi_teyidini_hesapla(snapshots[HAFTALIK])
    gunluk = zaman_dilimi_teyidini_hesapla(snapshots[GUNLUK])
    saatlik = zaman_dilimi_teyidini_hesapla(snapshots[SAATLIK])

    teyit_skoru = round(
        haftalik.skor * 0.30
        + gunluk.skor * 0.45
        + saatlik.skor * 0.25
    )
    teyit_durumu = _ortak_teyit_durumunu_belirle(
        haftalik=haftalik,
        gunluk=gunluk,
        saatlik=saatlik,
        teyit_skoru=teyit_skoru,
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

    return MultiTimeframeTechnicalConfirmation(
        sembol=paket.sembol,
        veri_kimligi=paket.veri_kimligi,
        analiz_kimligi=analiz_kimligi,
        haftalik=haftalik,
        gunluk=gunluk,
        saatlik=saatlik,
        teyit_skoru=int(teyit_skoru),
        teyit_durumu=teyit_durumu,
        pozitif_nedenler=pozitif_nedenler,
        riskler=riskler,
    )


def zaman_dilimi_teyidini_hesapla(
    snapshot: TimeframeSnapshot,
    pivot_genisligi: int = 2,
    hacim_esigi: float = 1.50,
) -> TimeframeConfirmationResult:
    """Tek zaman dilimi için trend, kırılım ve gösterge teyidi hesaplar."""
    if pivot_genisligi < 1:
        raise ValueError("Pivot genişliği en az 1 olmalıdır.")
    if hacim_esigi <= 1:
        raise ValueError("Hacim teyit eşiği 1'den büyük olmalıdır.")

    gostergeli = _gostergeleri_hazirla(snapshot)
    sma200_kullanilabilir = gostergeli["SMA200"].notna().sum() >= 2
    haftalik_sma200_fallback = (
        snapshot.ad.strip().casefold() == "Haftalık".casefold()
        and not sma200_kullanilabilir
    )

    zorunlu_sutunlar = list(_GOSTERGE_SUTUNLARI)
    if haftalik_sma200_fallback:
        zorunlu_sutunlar = [
            sutun
            for sutun in zorunlu_sutunlar
            if sutun != "SMA200"
        ]

    gecerli = gostergeli.dropna(subset=zorunlu_sutunlar)
    if len(gecerli) < 2:
        if haftalik_sma200_fallback:
            raise TechnicalConfirmationError(
                f"{snapshot.ad} teknik teyidi için SMA200 dışındaki "
                "geçerli göstergelerde en az iki satır gereklidir."
            )
        raise TechnicalConfirmationError(
            f"{snapshot.ad} teknik teyidi için SMA200 dahil en az iki "
            "geçerli gösterge satırı gereklidir."
        )

    son = gecerli.iloc[-1]
    onceki = gecerli.iloc[-2]

    ortalamalar = _hareketli_ortalama_teyidini_hesapla(
        onceki,
        son,
        sma200_kullanilabilir=not haftalik_sma200_fallback,
    )
    momentum = _momentum_teyidini_hesapla(onceki, son)
    kirilim = _trend_cizgisi_kirilimini_hesapla(
        veri=snapshot.veri,
        pivot_genisligi=pivot_genisligi,
        hacim_esigi=hacim_esigi,
    )

    try:
        seviyeler = destek_direnc_bul(
            snapshot.veri,
            bakis_periyodu=min(120, len(snapshot.veri)),
            pivot_genisligi=pivot_genisligi,
        )
    except (SupportResistanceError, ValueError) as hata:
        raise TechnicalConfirmationError(
            f"{snapshot.ad} destek/direnç analizi yapılamadı: {hata}"
        ) from hata

    skor, pozitif_nedenler, riskler = _zaman_dilimi_skorunu_hesapla(
        kapanis=float(son["Close"]),
        ortalamalar=ortalamalar,
        momentum=momentum,
        kirilim=kirilim,
    )

    return TimeframeConfirmationResult(
        ad=snapshot.ad,
        interval=snapshot.interval,
        son_zaman=pd.Timestamp(gecerli.index[-1]),
        kapanis=float(son["Close"]),
        destek=(None if seviyeler.destek is None else seviyeler.destek.fiyat),
        direnc=(None if seviyeler.direnc is None else seviyeler.direnc.fiyat),
        destek_gucu=(
            None if seviyeler.destek is None else seviyeler.destek.guc
        ),
        direnc_gucu=(
            None if seviyeler.direnc is None else seviyeler.direnc.guc
        ),
        kirilim=kirilim,
        ortalamalar=ortalamalar,
        momentum=momentum,
        skor=skor,
        yon=_yon_belirle(skor),
        pozitif_nedenler=tuple(pozitif_nedenler),
        riskler=tuple(riskler),
    )


def _gostergeleri_hazirla(snapshot: TimeframeSnapshot) -> pd.DataFrame:
    try:
        sonuc = teknik_gostergeleri_ekle(snapshot.veri)
    except (IndicatorError, ValueError) as hata:
        raise TechnicalConfirmationError(
            f"{snapshot.ad} göstergeleri hesaplanamadı: {hata}"
        ) from hata

    sonuc = sonuc.copy()
    sonuc["EMA55"] = ema(sonuc["Close"], 55)
    sonuc["SMA50"] = sonuc["Close"].rolling(50, min_periods=50).mean()
    sonuc["SMA200"] = sonuc["Close"].rolling(200, min_periods=200).mean()
    onceki_hacim_ortalamasi = (
        sonuc["Volume"].shift(1).rolling(20, min_periods=20).mean()
    )
    sonuc["Hacim_Orani_20"] = sonuc["Volume"] / onceki_hacim_ortalamasi
    return sonuc


def _hareketli_ortalama_teyidini_hesapla(
    onceki: pd.Series,
    son: pd.Series,
    *,
    sma200_kullanilabilir: bool = True,
) -> MovingAverageConfirmation:
    ema9_21 = _kesisim_durumu(
        onceki_hizli=float(onceki["EMA9"]),
        onceki_yavas=float(onceki["EMA21"]),
        hizli=float(son["EMA9"]),
        yavas=float(son["EMA21"]),
    )
    ema21_55 = _kesisim_durumu(
        onceki_hizli=float(onceki["EMA21"]),
        onceki_yavas=float(onceki["EMA55"]),
        hizli=float(son["EMA21"]),
        yavas=float(son["EMA55"]),
    )

    onceki_sma50 = float(onceki["SMA50"])
    sma50 = float(son["SMA50"])

    if sma200_kullanilabilir:
        onceki_sma200 = float(onceki["SMA200"])
        sma200 = float(son["SMA200"])

        golden_cross = (
            onceki_sma50 <= onceki_sma200
            and sma50 > sma200
        )
        death_cross = (
            onceki_sma50 >= onceki_sma200
            and sma50 < sma200
        )

        if golden_cross:
            uzun_vade = GOLDEN_CROSS
        elif death_cross:
            uzun_vade = DEATH_CROSS
        elif sma50 > sma200:
            uzun_vade = UZUN_VADE_POZITIF
        elif sma50 < sma200:
            uzun_vade = UZUN_VADE_NEGATIF
        else:
            uzun_vade = UZUN_VADE_ESIT
    else:
        sma200 = float("nan")
        golden_cross = False
        death_cross = False
        uzun_vade = UZUN_VADE_YETERSIZ

    return MovingAverageConfirmation(
        ema9=float(son["EMA9"]),
        ema21=float(son["EMA21"]),
        ema55=float(son["EMA55"]),
        sma50=sma50,
        sma200=sma200,
        ema9_21_durumu=ema9_21,
        ema21_55_durumu=ema21_55,
        uzun_vade_durumu=uzun_vade,
        golden_cross=golden_cross,
        death_cross=death_cross,
    )


def _kesisim_durumu(
    onceki_hizli: float,
    onceki_yavas: float,
    hizli: float,
    yavas: float,
) -> str:
    if onceki_hizli <= onceki_yavas and hizli > yavas:
        return EMA_POZITIF_KESISIM
    if onceki_hizli >= onceki_yavas and hizli < yavas:
        return EMA_NEGATIF_KESISIM
    if hizli > yavas:
        return EMA_POZITIF_YAPI
    if hizli < yavas:
        return EMA_NEGATIF_YAPI
    return EMA_ESIT


def _momentum_teyidini_hesapla(
    onceki: pd.Series,
    son: pd.Series,
) -> MomentumConfirmation:
    rsi14 = float(son["RSI14"])
    macd = float(son["MACD"])
    macd_sinyal = float(son["MACD_Sinyal"])
    histogram = float(son["MACD_Histogram"])
    onceki_histogram = float(onceki["MACD_Histogram"])
    histogram_gucleniyor = histogram > onceki_histogram

    if (
        50.0 <= rsi14 <= 75.0
        and macd > macd_sinyal
        and histogram > 0
        and histogram_gucleniyor
    ):
        durum = POZITIF
    elif (
        rsi14 < 45.0
        and macd < macd_sinyal
        and histogram < 0
        and not histogram_gucleniyor
    ):
        durum = NEGATIF
    else:
        durum = NOTR

    return MomentumConfirmation(
        rsi14=rsi14,
        macd=macd,
        macd_sinyal=macd_sinyal,
        macd_histogram=histogram,
        histogram_gucleniyor=histogram_gucleniyor,
        durum=durum,
    )


def _trend_cizgisi_kirilimini_hesapla(
    veri: pd.DataFrame,
    pivot_genisligi: int,
    hacim_esigi: float,
) -> TrendlineBreakoutResult:
    gerekli = {"High", "Low", "Close", "Volume"}
    eksikler = gerekli.difference(veri.columns)
    if eksikler:
        raise TechnicalConfirmationError(
            "Trend çizgisi analizi için eksik sütunlar: "
            + ", ".join(sorted(eksikler))
        )

    temiz = veri[["High", "Low", "Close", "Volume"]].dropna().sort_index()
    minimum = max(25, pivot_genisligi * 2 + 5)
    if len(temiz) < minimum:
        raise TechnicalConfirmationError(
            f"Trend çizgisi analizi için en az {minimum} satır gereklidir."
        )

    analiz_verisi = temiz.iloc[:-1]
    tepeler = _pivotlari_bul(
        analiz_verisi["High"], pivot_genisligi, yuksek=True
    )
    dipler = _pivotlari_bul(
        analiz_verisi["Low"], pivot_genisligi, yuksek=False
    )
    direnc_cizgisi = _uygun_trend_cizgisini_bul(
        tepeler, azalan=True, tip="Alçalan Direnç"
    )
    destek_cizgisi = _uygun_trend_cizgisini_bul(
        dipler, azalan=False, tip="Yükselen Destek"
    )

    son_konum = len(temiz) - 1
    onceki_konum = son_konum - 1
    son = temiz.iloc[-1]
    onceki = temiz.iloc[-2]
    hacim_orani = _hacim_orani_hesapla(temiz)
    hacim_teyidi = hacim_orani is not None and hacim_orani >= hacim_esigi

    adaylar: list[tuple[float, TrendlineBreakoutResult]] = []

    if direnc_cizgisi is not None:
        onceki_cizgi = direnc_cizgisi.deger(onceki_konum)
        cizgi = direnc_cizgisi.deger(son_konum)
        if onceki_cizgi > 0 and cizgi > 0:
            onceki_altinda = float(onceki["Close"]) <= onceki_cizgi
            kapanis_ustu = float(son["Close"]) > cizgi
            gun_ici_ustu = float(son["High"]) > cizgi
            if onceki_altinda and kapanis_ustu:
                oran = (float(son["Close"]) - cizgi) / cizgi
                adaylar.append(
                    (
                        abs(oran),
                        TrendlineBreakoutResult(
                            durum=TEYITLI_YUKARI_KIRILIM,
                            yon=POZITIF,
                            cizgi_tipi=direnc_cizgisi.tip,
                            cizgi_degeri=cizgi,
                            onceki_cizgi_degeri=onceki_cizgi,
                            pivot_sayisi=len(tepeler),
                            kapanis_teyidi=True,
                            erken_uyari=False,
                            hacim_orani=hacim_orani,
                            hacim_teyidi=hacim_teyidi,
                        ),
                    )
                )
            elif onceki_altinda and gun_ici_ustu and not kapanis_ustu:
                oran = (float(son["High"]) - cizgi) / cizgi
                adaylar.append(
                    (
                        abs(oran),
                        TrendlineBreakoutResult(
                            durum=ERKEN_YUKARI_UYARI,
                            yon=NOTR,
                            cizgi_tipi=direnc_cizgisi.tip,
                            cizgi_degeri=cizgi,
                            onceki_cizgi_degeri=onceki_cizgi,
                            pivot_sayisi=len(tepeler),
                            kapanis_teyidi=False,
                            erken_uyari=True,
                            hacim_orani=hacim_orani,
                            hacim_teyidi=hacim_teyidi,
                        ),
                    )
                )

    if destek_cizgisi is not None:
        onceki_cizgi = destek_cizgisi.deger(onceki_konum)
        cizgi = destek_cizgisi.deger(son_konum)
        if onceki_cizgi > 0 and cizgi > 0:
            onceki_ustunde = float(onceki["Close"]) >= onceki_cizgi
            kapanis_alti = float(son["Close"]) < cizgi
            gun_ici_alti = float(son["Low"]) < cizgi
            if onceki_ustunde and kapanis_alti:
                oran = (cizgi - float(son["Close"])) / cizgi
                adaylar.append(
                    (
                        abs(oran),
                        TrendlineBreakoutResult(
                            durum=TEYITLI_ASAGI_KIRILIM,
                            yon=NEGATIF,
                            cizgi_tipi=destek_cizgisi.tip,
                            cizgi_degeri=cizgi,
                            onceki_cizgi_degeri=onceki_cizgi,
                            pivot_sayisi=len(dipler),
                            kapanis_teyidi=True,
                            erken_uyari=False,
                            hacim_orani=hacim_orani,
                            hacim_teyidi=hacim_teyidi,
                        ),
                    )
                )
            elif onceki_ustunde and gun_ici_alti and not kapanis_alti:
                oran = (cizgi - float(son["Low"])) / cizgi
                adaylar.append(
                    (
                        abs(oran),
                        TrendlineBreakoutResult(
                            durum=ERKEN_ASAGI_UYARI,
                            yon=NOTR,
                            cizgi_tipi=destek_cizgisi.tip,
                            cizgi_degeri=cizgi,
                            onceki_cizgi_degeri=onceki_cizgi,
                            pivot_sayisi=len(dipler),
                            kapanis_teyidi=False,
                            erken_uyari=True,
                            hacim_orani=hacim_orani,
                            hacim_teyidi=hacim_teyidi,
                        ),
                    )
                )

    if adaylar:
        return max(adaylar, key=lambda aday: aday[0])[1]

    mevcut_cizgi = direnc_cizgisi or destek_cizgisi
    if mevcut_cizgi is None:
        return TrendlineBreakoutResult(
            durum=TREND_CIZGISI_YOK,
            yon=NOTR,
            cizgi_tipi="Yok",
            cizgi_degeri=None,
            onceki_cizgi_degeri=None,
            pivot_sayisi=max(len(tepeler), len(dipler)),
            kapanis_teyidi=False,
            erken_uyari=False,
            hacim_orani=hacim_orani,
            hacim_teyidi=False,
        )

    return TrendlineBreakoutResult(
        durum=KIRILIM_YOK,
        yon=NOTR,
        cizgi_tipi=mevcut_cizgi.tip,
        cizgi_degeri=mevcut_cizgi.deger(son_konum),
        onceki_cizgi_degeri=mevcut_cizgi.deger(onceki_konum),
        pivot_sayisi=(
            len(tepeler) if direnc_cizgisi is not None else len(dipler)
        ),
        kapanis_teyidi=False,
        erken_uyari=False,
        hacim_orani=hacim_orani,
        hacim_teyidi=False,
    )


def _pivotlari_bul(
    seri: pd.Series,
    genislik: int,
    yuksek: bool,
) -> list[_Pivot]:
    noktalar: list[_Pivot] = []
    for konum in range(genislik, len(seri) - genislik):
        fiyat = float(seri.iloc[konum])
        sol = seri.iloc[konum - genislik:konum]
        sag = seri.iloc[konum + 1:konum + genislik + 1]
        if yuksek:
            uygun = fiyat > float(sol.max()) and fiyat > float(sag.max())
        else:
            uygun = fiyat < float(sol.min()) and fiyat < float(sag.min())
        if uygun:
            noktalar.append(_Pivot(konum=konum, fiyat=fiyat))
    return noktalar


def _uygun_trend_cizgisini_bul(
    pivotlar: list[_Pivot],
    azalan: bool,
    tip: str,
) -> _TrendLine | None:
    for son_indeks in range(len(pivotlar) - 1, 0, -1):
        son = pivotlar[son_indeks]
        for ilk_indeks in range(son_indeks - 1, -1, -1):
            ilk = pivotlar[ilk_indeks]
            if son.konum - ilk.konum < 3:
                continue
            uygun = son.fiyat < ilk.fiyat if azalan else son.fiyat > ilk.fiyat
            if uygun:
                return _TrendLine(tip=tip, ilk=ilk, son=son)
    return None


def _hacim_orani_hesapla(veri: pd.DataFrame) -> float | None:
    onceki_hacimler = veri["Volume"].iloc[:-1].tail(20)
    if len(onceki_hacimler) < 20:
        return None
    ortalama = float(onceki_hacimler.mean())
    if ortalama <= 0:
        return None
    return float(veri["Volume"].iloc[-1]) / ortalama


def _zaman_dilimi_skorunu_hesapla(
    kapanis: float,
    ortalamalar: MovingAverageConfirmation,
    momentum: MomentumConfirmation,
    kirilim: TrendlineBreakoutResult,
) -> tuple[int, list[str], list[str]]:
    skor = 0
    pozitif: list[str] = []
    riskler: list[str] = []

    if kapanis > ortalamalar.ema21:
        skor += 10
        pozitif.append("Kapanış EMA21 üzerinde.")
    else:
        riskler.append("Kapanış EMA21 altında.")

    if ortalamalar.ema9 > ortalamalar.ema21:
        skor += 10
        pozitif.append("EMA9, EMA21 üzerinde.")
    else:
        riskler.append("EMA9, EMA21 altında.")

    if ortalamalar.ema21 > ortalamalar.ema55:
        skor += 10
        pozitif.append("EMA21, EMA55 üzerinde.")
    else:
        riskler.append("EMA21, EMA55 altında.")

    if ortalamalar.sma50 > ortalamalar.sma200:
        skor += 10
        pozitif.append("Uzun vadeli ortalama yapısı pozitif.")
    else:
        riskler.append("SMA50, SMA200 üzerinde değil.")

    if momentum.durum == POZITIF:
        skor += 20
        pozitif.append("RSI ve MACD ortak pozitif momentum teyidi veriyor.")
    elif momentum.durum == NOTR:
        skor += 10
        riskler.append("RSI ve MACD ortak yön teyidi vermiyor.")
    else:
        riskler.append("RSI ve MACD ortak negatif momentum gösteriyor.")

    if kirilim.durum == TEYITLI_YUKARI_KIRILIM:
        skor += 30
        pozitif.append("Alçalan trend çizgisi kapanışla yukarı kırıldı.")
        if kirilim.hacim_teyidi:
            skor += 10
            pozitif.append("Yukarı kırılım hacimle teyit edildi.")
        else:
            riskler.append("Yukarı kırılımda hacim teyidi yok.")
    elif kirilim.durum == ERKEN_YUKARI_UYARI:
        skor += 15
        riskler.append("Gün içi yukarı kırılım var; kapanış teyidi bekleniyor.")
    elif kirilim.durum == TEYITLI_ASAGI_KIRILIM:
        riskler.append("Yükselen destek çizgisi kapanışla aşağı kırıldı.")
        if kirilim.hacim_teyidi:
            riskler.append("Aşağı kırılım yüksek hacimle güçlendi.")
    elif kirilim.durum == ERKEN_ASAGI_UYARI:
        riskler.append("Gün içi aşağı kırılım var; kapanış teyidi bekleniyor.")
    elif kirilim.durum == TREND_CIZGISI_YOK:
        riskler.append("Kırılım değerlendirmesi için yeterli trend çizgisi yok.")
    else:
        riskler.append("Son tamamlanmış mumda yeni trend çizgisi kırılımı yok.")

    return min(100, int(skor)), pozitif, riskler


def _yon_belirle(skor: int) -> str:
    if skor >= 70:
        return POZITIF
    if skor >= 40:
        return NOTR
    return NEGATIF


def _zorunlu_zaman_dilimlerini_getir(
    paket: MultiTimeframeDataBundle,
) -> dict[str, TimeframeSnapshot]:
    snapshots: dict[str, TimeframeSnapshot] = {}
    for snapshot in paket.zaman_dilimleri:
        if snapshot.ad in {SAATLIK, GUNLUK, HAFTALIK}:
            if snapshot.ad in snapshots:
                raise TechnicalConfirmationError(
                    f"Yinelenen zaman dilimi bulundu: {snapshot.ad}"
                )
            snapshots[snapshot.ad] = snapshot

    eksikler = [
        ad for ad in (HAFTALIK, GUNLUK, SAATLIK) if ad not in snapshots
    ]
    if eksikler:
        raise TechnicalConfirmationError(
            "Teknik teyit için eksik zaman dilimleri: " + ", ".join(eksikler)
        )
    return snapshots


def _ortak_teyit_durumunu_belirle(
    haftalik: TimeframeConfirmationResult,
    gunluk: TimeframeConfirmationResult,
    saatlik: TimeframeConfirmationResult,
    teyit_skoru: int,
) -> str:
    if haftalik.yon == POZITIF and gunluk.yon == POZITIF:
        if teyit_skoru >= 70 and saatlik.yon != NEGATIF:
            return POZITIF_TEKNIK_TEYIT
        return TEYIT_BEKLENIYOR
    if haftalik.yon == NEGATIF and gunluk.yon == NEGATIF:
        if teyit_skoru < 40 and saatlik.yon != POZITIF:
            return NEGATIF_TEKNIK_TEYIT
        return TEYIT_BEKLENIYOR
    if {haftalik.yon, gunluk.yon} == {POZITIF, NEGATIF}:
        return CELISKILI_TEKNIK_GORUNUM
    return TEYIT_BEKLENIYOR


def _ortak_aciklamalari_olustur(
    haftalik: TimeframeConfirmationResult,
    gunluk: TimeframeConfirmationResult,
    saatlik: TimeframeConfirmationResult,
    teyit_durumu: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    pozitif: list[str] = []
    riskler: list[str] = []

    if haftalik.yon == POZITIF:
        pozitif.append("Haftalık teknik yapı pozitif.")
    elif haftalik.yon == NEGATIF:
        riskler.append("Haftalık teknik yapı negatif.")
    else:
        riskler.append("Haftalık teknik yapı nötr.")

    if gunluk.kirilim.durum == TEYITLI_YUKARI_KIRILIM:
        pozitif.append("Günlük trend çizgisi kırılımı kapanışla teyitli.")
    elif gunluk.kirilim.durum == TEYITLI_ASAGI_KIRILIM:
        riskler.append("Günlük trend çizgisi aşağı kırıldı.")
    elif gunluk.kirilim.erken_uyari:
        riskler.append("Günlük kırılım yalnızca erken uyarı aşamasında.")

    if saatlik.yon == POZITIF:
        pozitif.append("Saatlik teknik zamanlama pozitif.")
    elif saatlik.yon == NEGATIF:
        riskler.append("Saatlik teknik zamanlama negatif.")
    else:
        riskler.append("Saatlik teknik zamanlama nötr.")

    if teyit_durumu == CELISKILI_TEKNIK_GORUNUM:
        riskler.append("Haftalık ve günlük teknik yön birbiriyle çelişiyor.")
    elif teyit_durumu == POZITIF_TEKNIK_TEYIT:
        pozitif.append("Ana zaman dilimleri ortak pozitif teyit veriyor.")
    elif teyit_durumu == NEGATIF_TEKNIK_TEYIT:
        riskler.append("Ana zaman dilimleri ortak negatif teyit veriyor.")
    else:
        riskler.append("İşlem planı öncesinde ek teknik teyit gerekiyor.")

    return tuple(pozitif), tuple(riskler)


def _analiz_kimligi_uret(
    paket: MultiTimeframeDataBundle,
    haftalik: TimeframeConfirmationResult,
    gunluk: TimeframeConfirmationResult,
    saatlik: TimeframeConfirmationResult,
) -> str:
    icerik = "|".join(
        (
            paket.sembol,
            paket.veri_kimligi,
            f"{haftalik.skor}:{haftalik.kirilim.durum}",
            f"{gunluk.skor}:{gunluk.kirilim.durum}",
            f"{saatlik.skor}:{saatlik.kirilim.durum}",
        )
    ).encode("utf-8")
    return sha256(icerik).hexdigest()[:12]
