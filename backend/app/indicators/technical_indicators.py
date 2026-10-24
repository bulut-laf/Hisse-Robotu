from __future__ import annotations

import numpy as np
import pandas as pd


class IndicatorError(Exception):
    """Teknik gösterge hesaplama sırasında oluşan özel hata."""


def ema(
    kapanis: pd.Series,
    periyot: int,
) -> pd.Series:
    """
    Üstel hareketli ortalama hesaplar.

    EMA, yakın tarihli fiyatlara daha fazla ağırlık verir.
    """
    if periyot < 1:
        raise ValueError("EMA periyodu en az 1 olmalıdır.")

    return kapanis.ewm(
        span=periyot,
        adjust=False,
        min_periods=periyot,
    ).mean()


def rsi(
    kapanis: pd.Series,
    periyot: int = 14,
) -> pd.Series:
    """
    Wilder yaklaşımıyla RSI hesaplar.

    Genel değerlendirme:
        RSI > 70  : Aşırı alım riski
        RSI 50-70 : Pozitif momentum
        RSI 30-50 : Zayıf veya nötr momentum
        RSI < 30  : Aşırı satış bölgesi
    """
    if periyot < 2:
        raise ValueError("RSI periyodu en az 2 olmalıdır.")

    degisim = kapanis.diff()

    kazanc = degisim.clip(lower=0)
    kayip = -degisim.clip(upper=0)

    ortalama_kazanc = kazanc.ewm(
        alpha=1 / periyot,
        adjust=False,
        min_periods=periyot,
    ).mean()

    ortalama_kayip = kayip.ewm(
        alpha=1 / periyot,
        adjust=False,
        min_periods=periyot,
    ).mean()

    sonuc = pd.Series(
        np.nan,
        index=kapanis.index,
        dtype="float64",
        name=f"RSI{periyot}",
    )

    normal_durum = (
        (ortalama_kazanc > 0)
        & (ortalama_kayip > 0)
    )

    rs = (
        ortalama_kazanc[normal_durum]
        / ortalama_kayip[normal_durum]
    )

    sonuc.loc[normal_durum] = 100 - (100 / (1 + rs))

    # Fiyat yalnızca yükselmişse RSI 100.
    sonuc.loc[
        (ortalama_kazanc > 0)
        & (ortalama_kayip == 0)
    ] = 100.0

    # Fiyat yalnızca düşmüşse RSI 0.
    sonuc.loc[
        (ortalama_kazanc == 0)
        & (ortalama_kayip > 0)
    ] = 0.0

    # Hiç fiyat değişimi yoksa RSI nötr kabul edilir.
    sonuc.loc[
        (ortalama_kazanc == 0)
        & (ortalama_kayip == 0)
    ] = 50.0

    return sonuc


def macd(
    kapanis: pd.Series,
    hizli_periyot: int = 12,
    yavas_periyot: int = 26,
    sinyal_periyodu: int = 9,
) -> pd.DataFrame:
    """
    MACD, sinyal çizgisi ve histogramı hesaplar.
    """
    if hizli_periyot >= yavas_periyot:
        raise ValueError(
            "Hızlı MACD periyodu, yavaş periyottan küçük olmalıdır."
        )

    hizli_ema = ema(kapanis, hizli_periyot)
    yavas_ema = ema(kapanis, yavas_periyot)

    macd_cizgisi = hizli_ema - yavas_ema

    sinyal_cizgisi = macd_cizgisi.ewm(
        span=sinyal_periyodu,
        adjust=False,
        min_periods=sinyal_periyodu,
    ).mean()

    histogram = macd_cizgisi - sinyal_cizgisi

    return pd.DataFrame(
        {
            "MACD": macd_cizgisi,
            "MACD_Sinyal": sinyal_cizgisi,
            "MACD_Histogram": histogram,
        },
        index=kapanis.index,
    )


def atr(
    veri: pd.DataFrame,
    periyot: int = 14,
) -> pd.Series:
    """
    Average True Range hesaplar.

    ATR fiyat yönünü değil, fiyat hareketlerinin genişliğini
    ve dolayısıyla volatiliteyi ölçer.
    """
    gerekli_sutunlar = {"High", "Low", "Close"}

    eksik_sutunlar = gerekli_sutunlar.difference(veri.columns)

    if eksik_sutunlar:
        raise IndicatorError(
            "ATR için eksik sütunlar: "
            + ", ".join(sorted(eksik_sutunlar))
        )

    onceki_kapanis = veri["Close"].shift(1)

    gunluk_aralik = veri["High"] - veri["Low"]
    yuksek_onceki_kapanis = (
        veri["High"] - onceki_kapanis
    ).abs()
    dusuk_onceki_kapanis = (
        veri["Low"] - onceki_kapanis
    ).abs()

    true_range = pd.concat(
        [
            gunluk_aralik,
            yuksek_onceki_kapanis,
            dusuk_onceki_kapanis,
        ],
        axis=1,
    ).max(axis=1)

    return true_range.ewm(
        alpha=1 / periyot,
        adjust=False,
        min_periods=periyot,
    ).mean()


def teknik_gostergeleri_ekle(
    veri: pd.DataFrame,
) -> pd.DataFrame:
    """
    Temel teknik göstergeleri fiyat tablosuna ekler.

    Eklenen sütunlar:
        EMA9
        EMA21
        RSI14
        MACD
        MACD_Sinyal
        MACD_Histogram
        ATR14
        ATR_Yuzde
    """
    gerekli_sutunlar = {
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    }

    eksik_sutunlar = gerekli_sutunlar.difference(veri.columns)

    if eksik_sutunlar:
        raise IndicatorError(
            "Teknik analiz için eksik sütunlar: "
            + ", ".join(sorted(eksik_sutunlar))
        )

    sonuc = veri.copy()

    sonuc["EMA9"] = ema(
        sonuc["Close"],
        periyot=9,
    )

    sonuc["EMA21"] = ema(
        sonuc["Close"],
        periyot=21,
    )

    sonuc["RSI14"] = rsi(
        sonuc["Close"],
        periyot=14,
    )

    macd_sonuclari = macd(sonuc["Close"])

    sonuc[
        [
            "MACD",
            "MACD_Sinyal",
            "MACD_Histogram",
        ]
    ] = macd_sonuclari

    sonuc["ATR14"] = atr(
        sonuc,
        periyot=14,
    )

    sonuc["ATR_Yuzde"] = (
        sonuc["ATR14"]
        / sonuc["Close"]
        * 100
    )

    return sonuc