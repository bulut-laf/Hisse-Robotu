from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backend.app.backtest.backtest_models import (
    BacktestTrade,
    CIKIS_SURE_SONU,
)
from backend.app.backtest.portfolio_capacity_sensitivity import (
    PortfolioCapacitySensitivityAnalyzer,
    PortfolioCapacitySensitivityError,
)


def fiyat_verisi(
    kapanislar: list[float],
    baslangic: str = "2026-01-01",
) -> pd.DataFrame:
    tarihler = pd.date_range(
        baslangic,
        periods=len(kapanislar),
        freq="D",
    )
    return pd.DataFrame(
        {
            "Open": kapanislar,
            "Close": kapanislar,
        },
        index=tarihler,
    )


def islem(
    sembol: str,
    giris_gunu: int,
    cikis_gunu: int,
    giris: float,
    cikis: float,
    skor: int = 60,
) -> BacktestTrade:
    baslangic = date(2026, 1, 1)
    sinyal_tarihi = pd.Timestamp(baslangic) + pd.Timedelta(
        days=giris_gunu - 1
    )
    giris_tarihi = pd.Timestamp(baslangic) + pd.Timedelta(
        days=giris_gunu
    )
    cikis_tarihi = pd.Timestamp(baslangic) + pd.Timedelta(
        days=cikis_gunu
    )
    return BacktestTrade.olustur(
        sembol=sembol,
        sinyal_tarihi=sinyal_tarihi.date(),
        giris_tarihi=giris_tarihi.date(),
        cikis_tarihi=cikis_tarihi.date(),
        giris_fiyati=giris,
        cikis_fiyati=cikis,
        skor=skor,
        teknik_gorunum="Pozitif Teknik Görünüm",
        elde_tutulan_bar=max(1, cikis_gunu - giris_gunu + 1),
        cikis_nedeni=CIKIS_SURE_SONU,
        islem_maliyeti_orani=0.0,
    )


def ornek_veriler_ve_islemler():
    veriler = {
        "AAA.IS": fiyat_verisi([100, 100, 110]),
        "BBB.IS": fiyat_verisi([100, 100, 120]),
        "CCC.IS": fiyat_verisi([100, 100, 90]),
    }
    islemler = [
        islem("AAA.IS", 1, 2, 100, 110, skor=70),
        islem("BBB.IS", 1, 2, 100, 120, skor=80),
        islem("CCC.IS", 1, 2, 100, 90, skor=60),
    ]
    return veriler, islemler


def test_varsayilan_kapasiteler_sirali_ve_tek_raporda_uretilir() -> None:
    veriler, islemler = ornek_veriler_ve_islemler()

    rapor = PortfolioCapacitySensitivityAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        islem_maliyeti_orani=0.0,
    )

    assert [senaryo.kapasite for senaryo in rapor.senaryolar] == [1, 2, 3]


def test_kapasiteye_gore_pozisyon_payi_otomatik_hesaplanir() -> None:
    veriler, islemler = ornek_veriler_ve_islemler()

    rapor = PortfolioCapacitySensitivityAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        kapasiteler=[3, 1, 2],
        islem_maliyeti_orani=0.0,
    )

    assert [
        senaryo.pozisyon_basina_sermaye_orani
        for senaryo in rapor.senaryolar
    ] == pytest.approx([1.0, 0.5, 1.0 / 3.0])


def test_dusuk_kapasite_daha_fazla_islem_atlar() -> None:
    veriler, islemler = ornek_veriler_ve_islemler()

    rapor = PortfolioCapacitySensitivityAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        kapasiteler=[1, 3],
        islem_maliyeti_orani=0.0,
    )

    bir, uc = rapor.senaryolar
    assert bir.rapor.tamamlanan_islem_sayisi == 1
    assert bir.rapor.atlanan_islem_sayisi == 2
    assert uc.rapor.tamamlanan_islem_sayisi == 3
    assert uc.rapor.atlanan_islem_sayisi == 0


def test_ayni_aday_havuzunda_yuksek_skor_onceligi_korunur() -> None:
    veriler, islemler = ornek_veriler_ve_islemler()

    rapor = PortfolioCapacitySensitivityAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        kapasiteler=[1],
        islem_maliyeti_orani=0.0,
    )

    kabul = rapor.senaryolar[0].rapor.kabul_edilen_islemler
    assert [kayit.islem.sembol for kayit in kabul] == ["BBB.IS"]


def test_senaryolar_ayni_baslangic_sermayesini_kullanir() -> None:
    veriler, islemler = ornek_veriler_ve_islemler()

    rapor = PortfolioCapacitySensitivityAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        kapasiteler=[1, 2, 3],
        baslangic_sermayesi=250_000,
        islem_maliyeti_orani=0.0,
    )

    assert all(
        senaryo.rapor.baslangic_sermayesi == 250_000
        for senaryo in rapor.senaryolar
    )


def test_getiri_dusus_orani_raporlanir() -> None:
    veriler = {
        "AAA.IS": fiyat_verisi([100, 100, 80, 110]),
    }
    islemler = [islem("AAA.IS", 1, 3, 100, 110, skor=80)]

    rapor = PortfolioCapacitySensitivityAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        kapasiteler=[1],
        islem_maliyeti_orani=0.0,
    )

    senaryo = rapor.senaryolar[0]
    assert senaryo.rapor.toplam_getiri_orani == pytest.approx(0.10)
    assert senaryo.rapor.maksimum_dusus_orani == pytest.approx(0.20)
    assert senaryo.getiri_dusus_orani == pytest.approx(0.50)


def test_sifir_dususte_getiri_dusus_orani_hesaplanmaz() -> None:
    veriler = {"AAA.IS": fiyat_verisi([100, 100, 110])}
    islemler = [islem("AAA.IS", 1, 2, 100, 110)]

    rapor = PortfolioCapacitySensitivityAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        kapasiteler=[1],
        islem_maliyeti_orani=0.0,
    )

    assert rapor.senaryolar[0].getiri_dusus_orani is None
    assert rapor.en_iyi_getiri_dusus_senaryosu is None


def test_en_iyi_senaryo_ozetleri_deterministik_secillir() -> None:
    veriler, islemler = ornek_veriler_ve_islemler()

    rapor = PortfolioCapacitySensitivityAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        kapasiteler=[1, 2, 3],
        islem_maliyeti_orani=0.0,
    )

    assert rapor.en_yuksek_getiri_senaryosu is not None
    assert rapor.en_yuksek_getiri_senaryosu.kapasite == 1
    assert rapor.en_dusuk_dusus_senaryosu is not None
    assert rapor.en_dusuk_dusus_senaryosu.kapasite == 1


def test_gecersiz_kapasite_listeleri_hata_verir() -> None:
    analizci = PortfolioCapacitySensitivityAnalyzer()

    with pytest.raises(
        PortfolioCapacitySensitivityError,
        match="En az bir",
    ):
        analizci.analiz_et({}, [], kapasiteler=[])

    with pytest.raises(
        PortfolioCapacitySensitivityError,
        match="pozitif tam sayı",
    ):
        analizci.analiz_et({}, [], kapasiteler=[0, 2])

    with pytest.raises(
        PortfolioCapacitySensitivityError,
        match="tekrar etmemelidir",
    ):
        analizci.analiz_et({}, [], kapasiteler=[1, 1])
