from __future__ import annotations

import pandas as pd
import pytest

from backend.app.analysis.support_resistance import (
    SupportResistanceError,
    destek_direnc_bul,
)


def ornek_pivot_verisi() -> pd.DataFrame:
    """
    İkişer kez test edilmiş destek ve direnç kümeleri üretir.
    """
    tarihler = pd.date_range(
        start="2026-01-01",
        periods=11,
        freq="D",
    )

    return pd.DataFrame(
        {
            "High": [
                101.0,
                103.0,
                104.0,
                110.0,
                105.0,
                104.0,
                106.0,
                109.5,
                106.0,
                103.0,
                102.0,
            ],
            "Low": [
                99.0,
                97.0,
                94.0,
                98.0,
                99.0,
                97.0,
                94.5,
                98.0,
                99.0,
                98.0,
                99.0,
            ],
            "Close": [
                100.0,
                99.0,
                96.0,
                104.0,
                102.0,
                100.0,
                96.0,
                105.0,
                102.0,
                101.0,
                100.0,
            ],
        },
        index=tarihler,
    )


def test_destek_ve_direnc_dogru_bulunur() -> None:
    sonuc = destek_direnc_bul(
        veri=ornek_pivot_verisi(),
        bakis_periyodu=120,
        pivot_genisligi=2,
        birlestirme_toleransi_yuzde=1.00,
    )

    assert sonuc.mevcut_fiyat == pytest.approx(
        100.0,
        abs=1e-10,
    )

    assert sonuc.destek is not None
    assert sonuc.direnc is not None

    assert sonuc.destek.fiyat == pytest.approx(
        94.25,
        abs=1e-10,
    )
    assert sonuc.direnc.fiyat == pytest.approx(
        109.75,
        abs=1e-10,
    )

    assert sonuc.destek.temas_sayisi == 2
    assert sonuc.direnc.temas_sayisi == 2

    assert sonuc.destek.guc == "Orta"
    assert sonuc.direnc.guc == "Orta"

    assert sonuc.destek_uzaklik_yuzde == pytest.approx(
        5.75,
        abs=1e-10,
    )
    assert sonuc.direnc_uzaklik_yuzde == pytest.approx(
        9.75,
        abs=1e-10,
    )

    assert sonuc.pivot_dip_sayisi == 2
    assert sonuc.pivot_tepe_sayisi == 2


def test_pivot_olmayan_veride_seviye_bulunmaz() -> None:
    tarihler = pd.date_range(
        start="2026-01-01",
        periods=10,
        freq="D",
    )

    veri = pd.DataFrame(
        {
            "High": [
                float(deger)
                for deger in range(101, 111)
            ],
            "Low": [
                float(deger)
                for deger in range(99, 109)
            ],
            "Close": [
                float(deger)
                for deger in range(100, 110)
            ],
        },
        index=tarihler,
    )

    sonuc = destek_direnc_bul(
        veri=veri,
        pivot_genisligi=2,
    )

    assert sonuc.destek is None
    assert sonuc.direnc is None
    assert sonuc.destek_uzaklik_yuzde is None
    assert sonuc.direnc_uzaklik_yuzde is None
    assert sonuc.pivot_dip_sayisi == 0
    assert sonuc.pivot_tepe_sayisi == 0


def test_eksik_sutunlarda_anlamli_hata_verir() -> None:
    veri = ornek_pivot_verisi().drop(
        columns=["High"]
    )

    with pytest.raises(
        SupportResistanceError,
        match="eksik sütunlar",
    ):
        destek_direnc_bul(veri)


def test_yetersiz_veri_hata_verir() -> None:
    veri = ornek_pivot_verisi().head(5)

    with pytest.raises(
        SupportResistanceError,
        match="yeterli veri yok",
    ):
        destek_direnc_bul(
            veri=veri,
            pivot_genisligi=2,
        )


def test_gecersiz_parametreler_hata_verir() -> None:
    veri = ornek_pivot_verisi()

    gecersiz_parametreler = [
        {
            "bakis_periyodu": 0,
        },
        {
            "pivot_genisligi": 0,
        },
        {
            "birlestirme_toleransi_yuzde": 0,
        },
    ]

    for parametreler in gecersiz_parametreler:
        with pytest.raises(ValueError):
            destek_direnc_bul(
                veri=veri,
                **parametreler,
            )