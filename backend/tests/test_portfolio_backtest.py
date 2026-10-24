from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backend.app.backtest.backtest_models import (
    BacktestTrade,
    CIKIS_SURE_SONU,
)
from backend.app.backtest.portfolio_backtest import (
    PORTFOY_KAPASITE_NEDENI,
    PORTFOY_SEMBOL_CAKISMA_NEDENI,
    PortfolioBacktestAnalyzer,
    PortfolioBacktestConfig,
    PortfolioBacktestError,
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


def test_ayni_gun_kapasitede_yuksek_skor_oncelik_alir() -> None:
    veriler = {
        "AAA.IS": fiyat_verisi([100, 100, 110]),
        "BBB.IS": fiyat_verisi([100, 100, 105]),
        "CCC.IS": fiyat_verisi([100, 100, 120]),
    }
    islemler = [
        islem("AAA.IS", 1, 2, 100, 110, skor=70),
        islem("BBB.IS", 1, 2, 100, 105, skor=60),
        islem("CCC.IS", 1, 2, 100, 120, skor=80),
    ]

    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        yapilandirma=PortfolioBacktestConfig(
            baslangic_sermayesi=100_000,
            maksimum_es_zamanli_pozisyon=2,
            islem_maliyeti_orani=0.0,
        ),
    )

    assert [
        kayit.islem.sembol
        for kayit in rapor.kabul_edilen_islemler
    ] == ["CCC.IS", "AAA.IS"]
    assert rapor.atlanan_islem_sayisi == 1
    assert rapor.atlanan_islemler[0].neden == PORTFOY_KAPASITE_NEDENI


def test_cikis_gunu_sermaye_yeni_giriste_tekrar_kullanilmaz() -> None:
    veriler = {
        "AAA.IS": fiyat_verisi([100, 100, 110, 110]),
        "BBB.IS": fiyat_verisi([100, 100, 100, 110]),
    }
    islemler = [
        islem("AAA.IS", 1, 2, 100, 110, skor=80),
        islem("BBB.IS", 2, 3, 100, 110, skor=90),
    ]

    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        yapilandirma=PortfolioBacktestConfig(
            maksimum_es_zamanli_pozisyon=1,
            islem_maliyeti_orani=0.0,
        ),
    )

    assert rapor.tamamlanan_islem_sayisi == 1
    assert rapor.atlanan_islem_sayisi == 1
    assert rapor.atlanan_islemler[0].neden == PORTFOY_KAPASITE_NEDENI


def test_portfoy_kaldirac_kullanmadan_esit_slot_ayirir() -> None:
    veriler = {
        "AAA.IS": fiyat_verisi([100, 100, 110]),
        "BBB.IS": fiyat_verisi([100, 100, 120]),
    }
    islemler = [
        islem("AAA.IS", 1, 2, 100, 110, skor=70),
        islem("BBB.IS", 1, 2, 100, 120, skor=60),
    ]

    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        yapilandirma=PortfolioBacktestConfig(
            baslangic_sermayesi=100_000,
            maksimum_es_zamanli_pozisyon=2,
            pozisyon_basina_sermaye_orani=0.5,
            islem_maliyeti_orani=0.0,
        ),
    )

    assert [
        kayit.ayrilan_sermaye
        for kayit in rapor.kabul_edilen_islemler
    ] == pytest.approx([50_000, 50_000])
    assert rapor.bitis_sermayesi == pytest.approx(115_000)
    assert rapor.maksimum_es_zamanli_pozisyon == 2
    assert rapor.maksimum_sermaye_kullanim_orani == pytest.approx(1.0)


def test_gunluk_degerleme_acik_pozisyon_dususunu_yakalar() -> None:
    veriler = {
        "AAA.IS": fiyat_verisi([100, 100, 80, 100]),
    }
    islemler = [
        islem("AAA.IS", 1, 3, 100, 100),
    ]

    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        yapilandirma=PortfolioBacktestConfig(
            maksimum_es_zamanli_pozisyon=1,
            islem_maliyeti_orani=0.0,
        ),
    )

    assert rapor.toplam_getiri_orani == pytest.approx(0.0)
    assert rapor.maksimum_dusus_orani == pytest.approx(0.20)


def test_cikis_gununde_motorun_cikis_fiyati_kullanilir() -> None:
    veriler = {
        "AAA.IS": fiyat_verisi([100, 100, 150]),
    }
    islemler = [
        islem("AAA.IS", 1, 2, 100, 110),
    ]

    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        yapilandirma=PortfolioBacktestConfig(
            maksimum_es_zamanli_pozisyon=1,
            islem_maliyeti_orani=0.0,
        ),
    )

    assert rapor.bitis_sermayesi == pytest.approx(110_000)
    assert rapor.gunluk_noktalar[-1].ozsermaye == pytest.approx(110_000)


def test_sembol_bazli_net_katki_hesaplanir() -> None:
    veriler = {
        "AAA.IS": fiyat_verisi([100, 100, 110]),
        "BBB.IS": fiyat_verisi([100, 100, 90]),
    }
    islemler = [
        islem("AAA.IS", 1, 2, 100, 110),
        islem("BBB.IS", 1, 2, 100, 90),
    ]

    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        yapilandirma=PortfolioBacktestConfig(
            baslangic_sermayesi=100_000,
            maksimum_es_zamanli_pozisyon=2,
            pozisyon_basina_sermaye_orani=0.5,
            islem_maliyeti_orani=0.0,
        ),
    )

    katkilar = {katki.sembol: katki for katki in rapor.sembol_katkilari}
    assert katkilar["AAA.IS"].net_kar == pytest.approx(5_000)
    assert katkilar["BBB.IS"].net_kar == pytest.approx(-5_000)
    assert katkilar["AAA.IS"].baslangic_sermayesine_katki_orani == pytest.approx(0.05)
    assert rapor.bitis_sermayesi == pytest.approx(100_000)


def test_ayni_sembolde_es_zamanli_islem_atlanir() -> None:
    veriler = {
        "AAA.IS": fiyat_verisi([100, 100, 100, 110, 120]),
    }
    islemler = [
        islem("AAA.IS", 1, 3, 100, 110, skor=80),
        islem("AAA.IS", 2, 4, 100, 120, skor=70),
    ]

    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        yapilandirma=PortfolioBacktestConfig(
            maksimum_es_zamanli_pozisyon=2,
            islem_maliyeti_orani=0.0,
        ),
    )

    assert rapor.tamamlanan_islem_sayisi == 1
    assert rapor.atlanan_islemler[0].neden == PORTFOY_SEMBOL_CAKISMA_NEDENI


def test_islemsiz_rapor_baslangic_sermayesini_korur() -> None:
    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri={},
        islemler=[],
        yapilandirma=PortfolioBacktestConfig(
            baslangic_sermayesi=250_000,
        ),
    )

    assert rapor.bitis_sermayesi == 250_000
    assert rapor.toplam_getiri_orani == 0.0
    assert rapor.gunluk_noktalar == ()


def test_gecersiz_ayar_ve_eksik_fiyat_verisi_hata_verir() -> None:
    with pytest.raises(ValueError, match="eş zamanlı"):
        PortfolioBacktestConfig(
            maksimum_es_zamanli_pozisyon=0,
        )

    with pytest.raises(PortfolioBacktestError, match="fiyat verisi bulunamadı"):
        PortfolioBacktestAnalyzer().analiz_et(
            fiyat_verileri={},
            islemler=[islem("AAA.IS", 1, 2, 100, 110)],
        )
