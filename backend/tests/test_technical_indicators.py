from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.app.indicators.technical_indicators import (
    IndicatorError,
    atr,
    ema,
    macd,
    rsi,
    teknik_gostergeleri_ekle,
)


def sabit_fiyat_serisi(
    fiyat: float = 100.0,
    gun_sayisi: int = 60,
) -> pd.Series:
    tarih = pd.date_range(
        start="2026-01-01",
        periods=gun_sayisi,
        freq="D",
    )

    return pd.Series(
        [fiyat] * gun_sayisi,
        index=tarih,
        dtype="float64",
        name="Close",
    )


def ornek_fiyat_tablosu(
    gun_sayisi: int = 100,
) -> pd.DataFrame:
    tarih = pd.date_range(
        start="2026-01-01",
        periods=gun_sayisi,
        freq="D",
    )

    kapanis = np.linspace(
        100.0,
        150.0,
        gun_sayisi,
    )

    return pd.DataFrame(
        {
            "Open": kapanis - 0.50,
            "High": kapanis + 2.00,
            "Low": kapanis - 2.00,
            "Close": kapanis,
            "Volume": np.linspace(
                1_000_000,
                2_000_000,
                gun_sayisi,
            ),
        },
        index=tarih,
    )


def test_ema_sabit_fiyatta_sabit_kalir() -> None:
    sonuc = ema(
        sabit_fiyat_serisi(),
        periyot=9,
    )

    assert sonuc.dropna().iloc[-1] == pytest.approx(
        100.0,
        abs=1e-10,
    )


def test_rsi_sabit_fiyatta_elli_olur() -> None:
    sonuc = rsi(
        sabit_fiyat_serisi(),
        periyot=14,
    )

    assert sonuc.dropna().iloc[-1] == pytest.approx(
        50.0,
        abs=1e-10,
    )


def test_rsi_surekli_yukselen_fiyatta_yuz_olur() -> None:
    tarih = pd.date_range(
        start="2026-01-01",
        periods=60,
        freq="D",
    )

    kapanis = pd.Series(
        np.arange(100.0, 160.0),
        index=tarih,
    )

    sonuc = rsi(
        kapanis,
        periyot=14,
    )

    assert sonuc.dropna().iloc[-1] == pytest.approx(
        100.0,
        abs=1e-10,
    )


def test_macd_gerekli_sutunlari_uretir() -> None:
    kapanis = ornek_fiyat_tablosu()["Close"]

    sonuc = macd(kapanis)

    assert list(sonuc.columns) == [
        "MACD",
        "MACD_Sinyal",
        "MACD_Histogram",
    ]

    assert not sonuc["MACD"].dropna().empty
    assert not sonuc["MACD_Sinyal"].dropna().empty


def test_atr_sabit_gunluk_aralikta_dort_olur() -> None:
    veri = ornek_fiyat_tablosu()

    sonuc = atr(
        veri,
        periyot=14,
    )

    assert sonuc.dropna().iloc[-1] == pytest.approx(
        4.0,
        abs=0.01,
    )


def test_teknik_gostergeler_ana_sutunlari_ekler() -> None:
    sonuc = teknik_gostergeleri_ekle(
        ornek_fiyat_tablosu()
    )

    beklenen_sutunlar = {
        "EMA9",
        "EMA21",
        "RSI14",
        "MACD",
        "MACD_Sinyal",
        "MACD_Histogram",
        "ATR14",
        "ATR_Yuzde",
    }

    assert beklenen_sutunlar.issubset(
        sonuc.columns
    )

    son_satir = sonuc.dropna().iloc[-1]

    assert 0 <= son_satir["RSI14"] <= 100
    assert son_satir["ATR14"] > 0
    assert son_satir["ATR_Yuzde"] > 0


def test_eksik_sutunda_anlamli_hata_verir() -> None:
    eksik_veri = pd.DataFrame(
        {
            "Close": [100.0, 101.0, 102.0],
        }
    )

    with pytest.raises(
        IndicatorError,
        match="eksik sütunlar",
    ):
        teknik_gostergeleri_ekle(eksik_veri)