from __future__ import annotations

import pandas as pd
import pytest

from backend.app.analysis.signal_engine import (
    SignalEngineError,
    sinyal_uret,
)
from backend.app.risk.risk_engine import (
    risk_plani_olustur,
)


def risk_plani():
    """
    %3 ATR ve 1:2 risk/ödül oranına sahip
    orta volatiliteli örnek risk planı.
    """
    return risk_plani_olustur(
        giris_fiyati=100.0,
        atr=3.0,
        stop_atr_katsayisi=1.50,
        hedef_atr_katsayisi=3.00,
        minimum_risk_odul=2.00,
    )


def pozitif_sinyal_verisi() -> pd.DataFrame:
    """
    Güçlü trend, momentum ve hacim koşulları üretir.
    """
    tarihler = pd.date_range(
        start="2026-01-01",
        periods=5,
        freq="D",
    )

    return pd.DataFrame(
        {
            "Close": [
                99.0,
                100.0,
                103.0,
                105.0,
                108.0,
            ],
            "EMA9": [
                98.0,
                99.0,
                101.0,
                103.0,
                105.0,
            ],
            "EMA21": [
                100.0,
                100.0,
                100.0,
                101.0,
                102.0,
            ],
            "RSI14": [
                50.0,
                52.0,
                55.0,
                58.0,
                60.0,
            ],
            "MACD": [
                -0.20,
                0.10,
                0.50,
                1.20,
                2.00,
            ],
            "MACD_Sinyal": [
                0.00,
                0.00,
                0.20,
                0.60,
                1.00,
            ],
            "MACD_Histogram": [
                -0.20,
                0.10,
                0.30,
                0.60,
                1.00,
            ],
            "Hacim_Orani": [
                0.90,
                1.10,
                1.60,
                1.20,
                1.70,
            ],
            "Yukselis_Hacim_Patlamasi": [
                False,
                False,
                True,
                False,
                True,
            ],
            "Dusus_Hacim_Patlamasi": [
                False,
                False,
                False,
                False,
                False,
            ],
            "Gunluk_Getiri_Yuzde": [
                0.0,
                1.0,
                3.0,
                1.94,
                2.86,
            ],
        },
        index=tarihler,
    )


def negatif_sinyal_verisi() -> pd.DataFrame:
    """
    Zayıf trend, momentum ve hacim koşulları üretir.
    """
    tarihler = pd.date_range(
        start="2026-01-01",
        periods=5,
        freq="D",
    )

    return pd.DataFrame(
        {
            "Close": [
                105.0,
                103.0,
                101.0,
                99.0,
                97.0,
            ],
            "EMA9": [
                105.0,
                103.0,
                101.0,
                99.0,
                97.0,
            ],
            "EMA21": [
                100.0,
                101.0,
                102.0,
                103.0,
                104.0,
            ],
            "RSI14": [
                55.0,
                50.0,
                46.0,
                43.0,
                40.0,
            ],
            "MACD": [
                1.00,
                0.50,
                0.00,
                -0.50,
                -1.00,
            ],
            "MACD_Sinyal": [
                0.50,
                0.40,
                0.30,
                0.20,
                0.10,
            ],
            "MACD_Histogram": [
                0.50,
                0.10,
                -0.20,
                -0.50,
                -0.80,
            ],
            "Hacim_Orani": [
                0.90,
                0.85,
                0.80,
                0.75,
                0.80,
            ],
            "Yukselis_Hacim_Patlamasi": [
                False,
                False,
                False,
                False,
                False,
            ],
            "Dusus_Hacim_Patlamasi": [
                False,
                False,
                False,
                False,
                False,
            ],
            "Gunluk_Getiri_Yuzde": [
                0.0,
                -1.90,
                -1.94,
                -1.98,
                -2.02,
            ],
        },
        index=tarihler,
    )


def notr_sinyal_verisi() -> pd.DataFrame:
    """
    Pozitif trend fakat karışık momentum üreten veri.
    """
    tarihler = pd.date_range(
        start="2026-01-01",
        periods=5,
        freq="D",
    )

    return pd.DataFrame(
        {
            "Close": [
                101.0,
                102.0,
                103.0,
                104.0,
                105.0,
            ],
            "EMA9": [
                101.0,
                102.0,
                103.0,
                104.0,
                105.0,
            ],
            "EMA21": [
                100.0,
                100.0,
                100.0,
                100.0,
                100.0,
            ],
            "RSI14": [
                48.0,
                49.0,
                49.0,
                50.0,
                50.0,
            ],
            "MACD": [
                0.20,
                0.30,
                0.40,
                0.45,
                0.50,
            ],
            "MACD_Sinyal": [
                1.00,
                1.00,
                1.00,
                1.00,
                1.00,
            ],
            "MACD_Histogram": [
                -1.00,
                -0.80,
                -0.60,
                -0.40,
                -0.20,
            ],
            "Hacim_Orani": [
                0.90,
                0.95,
                1.00,
                1.05,
                1.10,
            ],
            "Yukselis_Hacim_Patlamasi": [
                False,
                False,
                False,
                False,
                False,
            ],
            "Dusus_Hacim_Patlamasi": [
                False,
                False,
                False,
                False,
                False,
            ],
            "Gunluk_Getiri_Yuzde": [
                0.0,
                0.99,
                0.98,
                0.97,
                0.96,
            ],
        },
        index=tarihler,
    )


def test_guclu_kosullarda_pozitif_sinyal_uretilir() -> None:
    sonuc = sinyal_uret(
        veri=pozitif_sinyal_verisi(),
        risk_plani=risk_plani(),
    )

    assert sonuc.skor == 96
    assert sonuc.trend_puani == 30
    assert sonuc.momentum_puani == 30
    assert sonuc.hacim_puani == 20
    assert sonuc.risk_puani == 16

    assert sonuc.karar == "Pozitif Teknik Görünüm"


def test_zayif_kosullarda_negatif_sinyal_uretilir() -> None:
    sonuc = sinyal_uret(
        veri=negatif_sinyal_verisi(),
        risk_plani=risk_plani(),
    )

    assert sonuc.skor == 20
    assert sonuc.trend_puani == 0
    assert sonuc.momentum_puani == 4
    assert sonuc.hacim_puani == 0
    assert sonuc.risk_puani == 16

    assert sonuc.karar == "Negatif Teknik Görünüm"


def test_karisik_kosullarda_notr_sinyal_uretilir() -> None:
    sonuc = sinyal_uret(
        veri=notr_sinyal_verisi(),
        risk_plani=risk_plani(),
    )

    assert sonuc.skor == 58
    assert sonuc.karar == "Nötr Teknik Görünüm"


def test_toplam_skor_alt_puanlarin_toplamidir() -> None:
    sonuc = sinyal_uret(
        veri=pozitif_sinyal_verisi(),
        risk_plani=risk_plani(),
    )

    alt_puanlar_toplami = (
        sonuc.trend_puani
        + sonuc.momentum_puani
        + sonuc.hacim_puani
        + sonuc.risk_puani
    )

    assert sonuc.skor == alt_puanlar_toplami
    assert 0 <= sonuc.skor <= 100


def test_eksik_sutunlarda_anlamli_hata_verir() -> None:
    veri = pozitif_sinyal_verisi().drop(
        columns=["MACD"]
    )

    with pytest.raises(
        SignalEngineError,
        match="eksik sütunlar",
    ):
        sinyal_uret(
            veri=veri,
            risk_plani=risk_plani(),
        )


def test_tek_satirla_sinyal_uretilmez() -> None:
    veri = pozitif_sinyal_verisi().tail(1)

    with pytest.raises(
        SignalEngineError,
        match="en az iki satır",
    ):
        sinyal_uret(
            veri=veri,
            risk_plani=risk_plani(),
        )