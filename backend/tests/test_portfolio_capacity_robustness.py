from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from backend.app.backtest.backtest_models import BacktestTrade, CIKIS_SURE_SONU
from backend.app.backtest.portfolio_capacity_robustness import (
    PIYASA_GUCLU,
    PIYASA_NOTR,
    PIYASA_ZAYIF,
    PortfolioCapacityRobustnessAnalyzer,
    PortfolioCapacityRobustnessError,
)


BASLANGIC = date(2026, 1, 1)


def fiyat_verisi(kapanislar: list[float]) -> pd.DataFrame:
    tarihler = pd.date_range(BASLANGIC, periods=len(kapanislar), freq="D")
    return pd.DataFrame(
        {"Open": kapanislar, "Close": kapanislar},
        index=tarihler,
    )


def islem(
    sembol: str,
    giris_indeksi: int,
    cikis_indeksi: int,
    giris: float,
    cikis: float,
    skor: int = 60,
) -> BacktestTrade:
    giris_tarihi = BASLANGIC + timedelta(days=giris_indeksi)
    cikis_tarihi = BASLANGIC + timedelta(days=cikis_indeksi)
    return BacktestTrade.olustur(
        sembol=sembol,
        sinyal_tarihi=giris_tarihi - timedelta(days=1),
        giris_tarihi=giris_tarihi,
        cikis_tarihi=cikis_tarihi,
        giris_fiyati=giris,
        cikis_fiyati=cikis,
        skor=skor,
        teknik_gorunum="Pozitif Teknik Görünüm",
        elde_tutulan_bar=max(1, cikis_indeksi - giris_indeksi + 1),
        cikis_nedeni=CIKIS_SURE_SONU,
        islem_maliyeti_orani=0.0,
    )


def uc_sembollu_ornek():
    veriler = {
        "AAA.IS": fiyat_verisi([100, 100, 110, 110, 120, 120, 130, 130]),
        "BBB.IS": fiyat_verisi([100, 100, 120, 120, 100, 100, 90, 90]),
        "CCC.IS": fiyat_verisi([100, 100, 90, 90, 110, 110, 140, 140]),
    }
    islemler = [
        islem("AAA.IS", 1, 2, 100, 110, skor=80),
        islem("BBB.IS", 1, 2, 100, 120, skor=70),
        islem("CCC.IS", 1, 2, 100, 90, skor=60),
        islem("AAA.IS", 4, 5, 120, 120, skor=80),
        islem("BBB.IS", 4, 5, 100, 100, skor=70),
        islem("CCC.IS", 4, 5, 110, 110, skor=60),
        islem("AAA.IS", 6, 7, 130, 130, skor=80),
        islem("BBB.IS", 6, 7, 90, 90, skor=70),
        islem("CCC.IS", 6, 7, 140, 140, skor=60),
    ]
    return veriler, islemler


def test_son_kayan_pencere_adima_oturmasa_da_rapora_eklenir() -> None:
    veriler, islemler = uc_sembollu_ornek()

    rapor = PortfolioCapacityRobustnessAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        kapasiteler=[1, 2, 3],
        pencere_bar_sayisi=4,
        adim_bar_sayisi=3,
        minimum_islem_sayisi=1,
        islem_maliyeti_orani=0.0,
    )

    assert [p.baslangic_tarihi for p in rapor.pencereler] == [
        BASLANGIC,
        BASLANGIC + timedelta(days=3),
        BASLANGIC + timedelta(days=4),
    ]


def test_yalnizca_giris_ve_cikisi_pencere_icinde_kalan_islemler_kullanilir() -> None:
    veriler = {"AAA.IS": fiyat_verisi([100] * 6)}
    islemler = [
        islem("AAA.IS", 1, 2, 100, 110),
        islem("AAA.IS", 2, 4, 100, 110),
    ]

    rapor = PortfolioCapacityRobustnessAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        kapasiteler=[1],
        pencere_bar_sayisi=4,
        adim_bar_sayisi=4,
        minimum_islem_sayisi=1,
        islem_maliyeti_orani=0.0,
    )

    assert rapor.pencereler[0].aday_islem_sayisi == 1


def test_yetersiz_islemli_pencereler_atlanir() -> None:
    veriler = {"AAA.IS": fiyat_verisi([100] * 8)}
    islemler = [islem("AAA.IS", 1, 2, 100, 110)]

    rapor = PortfolioCapacityRobustnessAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        pencere_bar_sayisi=4,
        adim_bar_sayisi=2,
        minimum_islem_sayisi=2,
        islem_maliyeti_orani=0.0,
    )

    assert rapor.pencereler == ()
    assert rapor.piyasa_getiri_medyan_orani is None


def test_piyasa_pencereleri_medyana_gore_guclu_zayif_notr_etiketlenir() -> None:
    veriler = {
        "AAA.IS": fiyat_verisi(
            [100, 100, 100, 150, 200, 200, 100, 100, 50, 50]
        )
    }
    islemler = [
        islem("AAA.IS", 1, 2, 100, 100),
        islem("AAA.IS", 4, 5, 200, 200),
        islem("AAA.IS", 7, 8, 100, 50),
    ]

    rapor = PortfolioCapacityRobustnessAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        kapasiteler=[1],
        pencere_bar_sayisi=4,
        adim_bar_sayisi=3,
        minimum_islem_sayisi=1,
        islem_maliyeti_orani=0.0,
    )

    gruplar = {pencere.piyasa_grubu for pencere in rapor.pencereler}
    assert PIYASA_GUCLU in gruplar
    assert PIYASA_ZAYIF in gruplar
    assert PIYASA_NOTR in gruplar


def test_kapasite_ozetleri_pozitif_oran_ve_liderlikleri_hesaplar() -> None:
    veriler, islemler = uc_sembollu_ornek()

    rapor = PortfolioCapacityRobustnessAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        kapasiteler=[1, 2, 3],
        pencere_bar_sayisi=4,
        adim_bar_sayisi=3,
        minimum_islem_sayisi=1,
        islem_maliyeti_orani=0.0,
    )

    ozet = rapor.kapasite_ozeti(1)
    assert ozet is not None
    assert ozet.pencere_sayisi == len(rapor.pencereler)
    assert 0.0 <= ozet.pozitif_pencere_orani <= 1.0
    assert ozet.getiri_liderligi_sayisi >= 1


def test_tam_sepet_ve_her_bir_sembol_icin_dislamalar_uretilir() -> None:
    veriler, islemler = uc_sembollu_ornek()

    rapor = PortfolioCapacityRobustnessAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        kapasiteler=[1, 2, 3],
        pencere_bar_sayisi=4,
        adim_bar_sayisi=3,
        minimum_islem_sayisi=1,
        islem_maliyeti_orani=0.0,
    )

    assert [s.dislanan_sembol for s in rapor.sembol_dislamalari] == [
        None,
        "AAA.IS",
        "BBB.IS",
        "CCC.IS",
    ]


def test_dislanan_sembolun_islemleri_senaryoya_girmez() -> None:
    veriler, islemler = uc_sembollu_ornek()

    rapor = PortfolioCapacityRobustnessAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        kapasiteler=[1],
        pencere_bar_sayisi=4,
        adim_bar_sayisi=3,
        minimum_islem_sayisi=1,
        islem_maliyeti_orani=0.0,
    )

    aaa_disarida = next(
        senaryo
        for senaryo in rapor.sembol_dislamalari
        if senaryo.dislanan_sembol == "AAA.IS"
    )
    assert aaa_disarida.aday_islem_sayisi == 6
    assert "AAA.IS" not in aaa_disarida.dahil_semboller


def test_tek_sembolde_bos_dislamaya_gidilmez() -> None:
    veriler = {"AAA.IS": fiyat_verisi([100, 100, 110, 110])}
    islemler = [islem("AAA.IS", 1, 2, 100, 110)]

    rapor = PortfolioCapacityRobustnessAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        kapasiteler=[1],
        pencere_bar_sayisi=4,
        adim_bar_sayisi=1,
        minimum_islem_sayisi=1,
        islem_maliyeti_orani=0.0,
    )

    assert len(rapor.sembol_dislamalari) == 1
    assert rapor.sembol_dislamalari[0].dislanan_sembol is None


def test_gecersiz_pencere_ayarlari_hata_verir() -> None:
    analizci = PortfolioCapacityRobustnessAnalyzer()
    veriler = {"AAA.IS": fiyat_verisi([100, 100])}

    for alan, deger in (
        ("pencere_bar_sayisi", 0),
        ("adim_bar_sayisi", -1),
        ("minimum_islem_sayisi", True),
    ):
        kwargs = {
            "pencere_bar_sayisi": 2,
            "adim_bar_sayisi": 1,
            "minimum_islem_sayisi": 1,
        }
        kwargs[alan] = deger
        with pytest.raises(
            PortfolioCapacityRobustnessError,
            match="pozitif tam sayı",
        ):
            analizci.analiz_et(veriler, [], **kwargs)


def test_gecersiz_fiyat_verisi_acik_hata_verir() -> None:
    analizci = PortfolioCapacityRobustnessAnalyzer()

    with pytest.raises(
        PortfolioCapacityRobustnessError,
        match="En az bir sembole",
    ):
        analizci.analiz_et({}, [])

    with pytest.raises(
        PortfolioCapacityRobustnessError,
        match="Close sütunu",
    ):
        analizci.analiz_et(
            {"AAA.IS": pd.DataFrame({"Open": [100]}, index=[pd.Timestamp(BASLANGIC)])},
            [],
        )
