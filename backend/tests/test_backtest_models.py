from __future__ import annotations

from datetime import date

import pytest

from backend.app.backtest.backtest_models import (
    BacktestConfig,
    BacktestMetrics,
    BacktestSignal,
    BacktestTrade,
    CIKIS_HEDEF,
    CIKIS_SURE_SONU,
    CIKIS_ZARAR_DURDUR,
)


def ornek_islem(
    cikis_fiyati: float,
    sinyal_gunu: int,
    cikis_nedeni: str = CIKIS_SURE_SONU,
) -> BacktestTrade:
    return BacktestTrade.olustur(
        sembol="AAA.IS",
        sinyal_tarihi=date(
            2026,
            1,
            sinyal_gunu,
        ),
        giris_tarihi=date(
            2026,
            1,
            sinyal_gunu + 1,
        ),
        cikis_tarihi=date(
            2026,
            1,
            sinyal_gunu + 2,
        ),
        giris_fiyati=100.0,
        cikis_fiyati=cikis_fiyati,
        skor=70,
        teknik_gorunum=(
            "Pozitif Teknik Görünüm"
        ),
        elde_tutulan_bar=1,
        cikis_nedeni=cikis_nedeni,
        islem_maliyeti_orani=0.0,
    )


def test_varsayilan_backtest_yapilandirmasi_gecerlidir() -> None:
    yapilandirma = BacktestConfig()

    assert yapilandirma.elde_tutma_gunu == 10
    assert yapilandirma.minimum_skor == 50
    assert yapilandirma.baslangic_sermayesi == pytest.approx(
        100_000.0
    )
    assert yapilandirma.pozisyon_orani == pytest.approx(
        1.0
    )
    assert (
        yapilandirma.islem_maliyeti_orani
        == pytest.approx(0.001)
    )


def test_gecersiz_yapilandirma_degerleri_hata_verir() -> None:
    gecersiz_degerler = [
        {
            "elde_tutma_gunu": 0,
        },
        {
            "elde_tutma_gunu": 31,
        },
        {
            "minimum_skor": -1,
        },
        {
            "minimum_skor": 101,
        },
        {
            "baslangic_sermayesi": 0,
        },
        {
            "pozisyon_orani": 0,
        },
        {
            "pozisyon_orani": 1.01,
        },
        {
            "islem_maliyeti_orani": -0.01,
        },
        {
            "islem_maliyeti_orani": 0.10,
        },
        {
            "zarar_durdur_orani": 0,
        },
        {
            "hedef_orani": 1,
        },
    ]

    for degerler in gecersiz_degerler:
        with pytest.raises(ValueError):
            BacktestConfig(**degerler)


def test_sinyal_normalize_edilir_ve_dogrulanir() -> None:
    sinyal = BacktestSignal(
        sembol=" thyao.is ",
        sinyal_tarihi=date(
            2026,
            1,
            5,
        ),
        skor=75,
        teknik_gorunum=(
            "Pozitif Teknik Görünüm"
        ),
    )

    assert sinyal.sembol == "THYAO.IS"

    with pytest.raises(ValueError):
        BacktestSignal(
            sembol="",
            sinyal_tarihi=date(
                2026,
                1,
                5,
            ),
            skor=75,
            teknik_gorunum=(
                "Pozitif Teknik Görünüm"
            ),
        )

    with pytest.raises(ValueError):
        BacktestSignal(
            sembol="AAA.IS",
            sinyal_tarihi=date(
                2026,
                1,
                5,
            ),
            skor=101,
            teknik_gorunum=(
                "Pozitif Teknik Görünüm"
            ),
        )


def test_islem_brut_ve_net_getiriyi_hesaplar() -> None:
    islem = BacktestTrade.olustur(
        sembol=" aaa.is ",
        sinyal_tarihi=date(
            2026,
            1,
            1,
        ),
        giris_tarihi=date(
            2026,
            1,
            2,
        ),
        cikis_tarihi=date(
            2026,
            1,
            10,
        ),
        giris_fiyati=100.0,
        cikis_fiyati=110.0,
        skor=70,
        teknik_gorunum=(
            "Pozitif Teknik Görünüm"
        ),
        elde_tutulan_bar=6,
        cikis_nedeni=CIKIS_HEDEF,
        islem_maliyeti_orani=0.001,
    )

    beklenen_net_getiri = (
        110.0
        * 0.999
        / (
            100.0
            * 1.001
        )
    ) - 1

    assert islem.sembol == "AAA.IS"
    assert islem.brut_getiri_orani == pytest.approx(
        0.10
    )
    assert islem.net_getiri_orani == pytest.approx(
        beklenen_net_getiri
    )


def test_gecersiz_islem_degerleri_hata_verir() -> None:
    ortak = {
        "sembol": "AAA.IS",
        "sinyal_tarihi": date(
            2026,
            1,
            1,
        ),
        "giris_tarihi": date(
            2026,
            1,
            2,
        ),
        "cikis_tarihi": date(
            2026,
            1,
            3,
        ),
        "giris_fiyati": 100.0,
        "cikis_fiyati": 105.0,
        "skor": 70,
        "teknik_gorunum": (
            "Pozitif Teknik Görünüm"
        ),
        "elde_tutulan_bar": 1,
        "cikis_nedeni": CIKIS_SURE_SONU,
    }

    gecersiz_degerler = [
        {
            **ortak,
            "giris_tarihi": date(
                2026,
                1,
                1,
            ),
        },
        {
            **ortak,
            "cikis_tarihi": date(
                2026,
                1,
                1,
            ),
        },
        {
            **ortak,
            "giris_fiyati": 0,
        },
        {
            **ortak,
            "cikis_fiyati": 0,
        },
        {
            **ortak,
            "elde_tutulan_bar": 0,
        },
        {
            **ortak,
            "cikis_nedeni": "Bilinmeyen",
        },
    ]

    for degerler in gecersiz_degerler:
        with pytest.raises(ValueError):
            BacktestTrade.olustur(
                **degerler
            )


def test_bos_islem_listesi_sifir_metrik_uretir() -> None:
    yapilandirma = BacktestConfig(
        baslangic_sermayesi=50_000.0
    )

    metrikler = BacktestMetrics.hesapla(
        islemler=(),
        yapilandirma=yapilandirma,
    )

    assert metrikler.islem_sayisi == 0
    assert metrikler.kazanma_orani == 0
    assert metrikler.toplam_net_getiri_orani == 0
    assert metrikler.bitis_sermayesi == pytest.approx(
        50_000.0
    )
    assert metrikler.en_iyi_islem_orani is None
    assert metrikler.en_kotu_islem_orani is None
    assert metrikler.kar_faktoru is None


def test_coklu_islemlerin_performansi_hesaplanir() -> None:
    islemler = (
        ornek_islem(
            cikis_fiyati=110.0,
            sinyal_gunu=1,
            cikis_nedeni=CIKIS_HEDEF,
        ),
        ornek_islem(
            cikis_fiyati=95.0,
            sinyal_gunu=5,
            cikis_nedeni=CIKIS_ZARAR_DURDUR,
        ),
        ornek_islem(
            cikis_fiyati=120.0,
            sinyal_gunu=10,
            cikis_nedeni=CIKIS_HEDEF,
        ),
    )

    yapilandirma = BacktestConfig(
        baslangic_sermayesi=100_000.0,
        pozisyon_orani=0.50,
        islem_maliyeti_orani=0.0,
    )

    metrikler = BacktestMetrics.hesapla(
        islemler=islemler,
        yapilandirma=yapilandirma,
    )

    assert metrikler.islem_sayisi == 3
    assert metrikler.kazanan_islem_sayisi == 2
    assert metrikler.kaybeden_islem_sayisi == 1
    assert metrikler.basabas_islem_sayisi == 0
    assert metrikler.kazanma_orani == pytest.approx(
        2 / 3
    )
    assert (
        metrikler.ortalama_net_getiri_orani
        == pytest.approx(
            (
                0.10
                - 0.05
                + 0.20
            )
            / 3
        )
    )
    assert metrikler.bitis_sermayesi == pytest.approx(
        112_612.50
    )
    assert (
        metrikler.toplam_net_getiri_orani
        == pytest.approx(0.126125)
    )
    assert metrikler.en_iyi_islem_orani == pytest.approx(
        0.20
    )
    assert metrikler.en_kotu_islem_orani == pytest.approx(
        -0.05
    )
    assert metrikler.kar_faktoru == pytest.approx(
        6.0
    )


def test_maksimum_ardisik_kayip_hesaplanir() -> None:
    islemler = (
        ornek_islem(
            cikis_fiyati=90.0,
            sinyal_gunu=1,
        ),
        ornek_islem(
            cikis_fiyati=80.0,
            sinyal_gunu=5,
        ),
        ornek_islem(
            cikis_fiyati=105.0,
            sinyal_gunu=10,
        ),
        ornek_islem(
            cikis_fiyati=99.0,
            sinyal_gunu=15,
        ),
    )

    metrikler = BacktestMetrics.hesapla(
        islemler=islemler,
        yapilandirma=BacktestConfig(
            islem_maliyeti_orani=0.0
        ),
    )

    assert metrikler.maksimum_ardisik_kayip == 2
    assert metrikler.kar_faktoru == pytest.approx(
        0.05 / 0.31
    )