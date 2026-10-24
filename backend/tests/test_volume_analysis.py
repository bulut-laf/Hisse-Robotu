from __future__ import annotations

import pandas as pd
import pytest

from backend.app.analysis.volume_analysis import (
    VolumeAnalysisError,
    hacim_gostergelerini_ekle,
    son_hacim_ozeti,
)


def hacim_test_verisi(
    son_kapanis: float = 102.0,
    son_hacim: float = 1_600.0,
) -> pd.DataFrame:
    """
    Önceki 20 günün hacmi 1.000 olan sentetik veri üretir.

    Son günün hacmi 1.600 olduğunda:
        Hacim oranı = 1.600 / 1.000 = 1,60
    """
    tarihler = pd.date_range(
        start="2026-01-01",
        periods=21,
        freq="D",
    )

    kapanislar = [100.0] * 20 + [son_kapanis]
    hacimler = [1_000.0] * 20 + [son_hacim]

    return pd.DataFrame(
        {
            "Close": kapanislar,
            "Volume": hacimler,
        },
        index=tarihler,
    )


def test_guncel_hacim_kendi_ortalamasina_dahil_edilmez() -> None:
    veri = hacim_test_verisi(
        son_hacim=2_000.0,
    )

    sonuc = hacim_gostergelerini_ekle(veri)

    son = sonuc.iloc[-1]

    # Son günün yüksek hacmi ortalamaya dahil edilmemelidir.
    assert son["Ortalama_Hacim_20"] == pytest.approx(
        1_000.0,
        abs=1e-10,
    )

    assert son["Hacim_Orani"] == pytest.approx(
        2.0,
        abs=1e-10,
    )


def test_yukselen_fiyatta_hacim_patlamasi_belirlenir() -> None:
    veri = hacim_test_verisi(
        son_kapanis=102.0,
        son_hacim=1_600.0,
    )

    sonuc = hacim_gostergelerini_ekle(
        veri,
        patlama_esigi=1.50,
    )

    son = sonuc.iloc[-1]

    assert bool(son["Hacim_Patlamasi"]) is True
    assert bool(son["Yukselis_Hacim_Patlamasi"]) is True
    assert bool(son["Dusus_Hacim_Patlamasi"]) is False

    assert (
        son["Fiyat_Hacim_Durumu"]
        == "Yükseliş Hacim Onayı"
    )


def test_dusen_fiyatta_hacim_baskisi_belirlenir() -> None:
    veri = hacim_test_verisi(
        son_kapanis=98.0,
        son_hacim=1_600.0,
    )

    sonuc = hacim_gostergelerini_ekle(
        veri,
        patlama_esigi=1.50,
    )

    son = sonuc.iloc[-1]

    assert bool(son["Hacim_Patlamasi"]) is True
    assert bool(son["Yukselis_Hacim_Patlamasi"]) is False
    assert bool(son["Dusus_Hacim_Patlamasi"]) is True

    assert (
        son["Fiyat_Hacim_Durumu"]
        == "Düşüş Hacim Baskısı"
    )


def test_dusuk_hacimde_patlama_olusmaz() -> None:
    veri = hacim_test_verisi(
        son_kapanis=102.0,
        son_hacim=800.0,
    )

    sonuc = hacim_gostergelerini_ekle(veri)

    son = sonuc.iloc[-1]

    assert son["Hacim_Orani"] == pytest.approx(
        0.80,
        abs=1e-10,
    )

    assert bool(son["Hacim_Patlamasi"]) is False

    assert (
        son["Fiyat_Hacim_Durumu"]
        == "Düşük/Normal Hacim"
    )


def test_son_hacim_ozeti_dogru_degerleri_uretir() -> None:
    veri = hacim_test_verisi(
        son_kapanis=102.0,
        son_hacim=1_600.0,
    )

    analiz = hacim_gostergelerini_ekle(veri)
    ozet = son_hacim_ozeti(analiz)

    assert ozet["hacim"] == 1_600
    assert ozet["ortalama_hacim"] == 1_000
    assert ozet["hacim_orani"] == 1.60
    assert ozet["gunluk_getiri_yuzde"] == 2.0
    assert ozet["hacim_patlamasi"] is True
    assert ozet["durum"] == "Yükseliş Hacim Onayı"


def test_eksik_sutunlarda_anlamli_hata_verir() -> None:
    eksik_veri = pd.DataFrame(
        {
            "Close": [100.0, 101.0],
        }
    )

    with pytest.raises(
        VolumeAnalysisError,
        match="eksik sütunlar",
    ):
        hacim_gostergelerini_ekle(eksik_veri)