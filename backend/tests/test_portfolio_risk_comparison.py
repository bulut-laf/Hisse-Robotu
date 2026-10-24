from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backend.app.backtest.backtest_models import BacktestTrade, CIKIS_SURE_SONU
from backend.app.backtest.portfolio_backtest import (
    BOYUTLANDIRMA_RISK,
    BOYUTLANDIRMA_SABIT,
    PORTFOY_KAPASITE_NEDENI,
    PORTFOY_RISK_LIMITI_NEDENI,
    PortfolioBacktestAnalyzer,
    PortfolioBacktestConfig,
)
from backend.app.backtest.portfolio_risk_comparison import (
    PortfolioRiskComparisonAnalyzer,
)


def fiyat_verisi(kapanislar: list[float]) -> pd.DataFrame:
    tarihler = pd.date_range("2026-01-01", periods=len(kapanislar), freq="D")
    return pd.DataFrame(
        {
            "Open": kapanislar,
            "Close": kapanislar,
        },
        index=tarihler,
    )


def islem(
    sembol: str,
    giris_gunu: int = 1,
    cikis_gunu: int = 2,
    giris: float = 100.0,
    cikis: float = 110.0,
    skor: int = 60,
) -> BacktestTrade:
    baslangic = pd.Timestamp(date(2026, 1, 1))
    return BacktestTrade.olustur(
        sembol=sembol,
        sinyal_tarihi=(baslangic + pd.Timedelta(days=giris_gunu - 1)).date(),
        giris_tarihi=(baslangic + pd.Timedelta(days=giris_gunu)).date(),
        cikis_tarihi=(baslangic + pd.Timedelta(days=cikis_gunu)).date(),
        giris_fiyati=giris,
        cikis_fiyati=cikis,
        skor=skor,
        teknik_gorunum="Pozitif Teknik Görünüm",
        elde_tutulan_bar=max(1, cikis_gunu - giris_gunu + 1),
        cikis_nedeni=CIKIS_SURE_SONU,
        islem_maliyeti_orani=0.0,
    )


def risk_ayarlari(**degisiklikler) -> PortfolioBacktestConfig:
    ayarlar = {
        "baslangic_sermayesi": 100_000.0,
        "maksimum_es_zamanli_pozisyon": 3,
        "pozisyon_basina_sermaye_orani": 1 / 3,
        "islem_maliyeti_orani": 0.0,
        "boyutlandirma_modu": BOYUTLANDIRMA_RISK,
        "zarar_durdur_orani": 0.05,
        "islem_basina_risk_orani": 0.01,
        "toplam_acik_risk_orani": 0.02,
    }
    ayarlar.update(degisiklikler)
    return PortfolioBacktestConfig(**ayarlar)


def test_risk_modu_gerekli_risk_ayarlarini_ister() -> None:
    with pytest.raises(ValueError, match="zarar durdur"):
        PortfolioBacktestConfig(
            boyutlandirma_modu=BOYUTLANDIRMA_RISK,
            islem_basina_risk_orani=0.01,
            toplam_acik_risk_orani=0.02,
        )

    with pytest.raises(ValueError, match="küçük olamaz"):
        PortfolioBacktestConfig(
            boyutlandirma_modu=BOYUTLANDIRMA_RISK,
            zarar_durdur_orani=0.05,
            islem_basina_risk_orani=0.02,
            toplam_acik_risk_orani=0.01,
        )


def test_risk_butcesi_stop_mesafesine_gore_pozisyonu_hesaplar() -> None:
    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri={"AAA.IS": fiyat_verisi([100, 100, 110])},
        islemler=[islem("AAA.IS")],
        yapilandirma=risk_ayarlari(),
    )

    kayit = rapor.kabul_edilen_islemler[0]
    assert kayit.ayrilan_sermaye == pytest.approx(20_000.0)
    assert kayit.planlanan_risk_tutari == pytest.approx(1_000.0)


def test_pozisyon_sermaye_tavani_risk_boyutunu_sinirlar() -> None:
    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri={"AAA.IS": fiyat_verisi([100, 100, 110])},
        islemler=[islem("AAA.IS")],
        yapilandirma=risk_ayarlari(
            pozisyon_basina_sermaye_orani=0.10,
        ),
    )

    kayit = rapor.kabul_edilen_islemler[0]
    assert kayit.ayrilan_sermaye == pytest.approx(10_000.0)
    assert kayit.planlanan_risk_tutari == pytest.approx(500.0)


def test_toplam_acik_risk_limiti_ucuncu_islemi_atlar() -> None:
    veriler = {
        "AAA.IS": fiyat_verisi([100, 100, 110]),
        "BBB.IS": fiyat_verisi([100, 100, 110]),
        "CCC.IS": fiyat_verisi([100, 100, 110]),
    }
    islemler = [
        islem("AAA.IS", skor=80),
        islem("BBB.IS", skor=70),
        islem("CCC.IS", skor=60),
    ]

    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        yapilandirma=risk_ayarlari(),
    )

    assert rapor.tamamlanan_islem_sayisi == 2
    assert rapor.atlanan_islem_sayisi == 1
    assert rapor.atlanan_islemler[0].neden == PORTFOY_RISK_LIMITI_NEDENI


def test_kapasite_limiti_risk_limitinden_bagimsiz_korunur() -> None:
    veriler = {
        "AAA.IS": fiyat_verisi([100, 100, 110]),
        "BBB.IS": fiyat_verisi([100, 100, 110]),
    }
    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=[islem("AAA.IS", skor=80), islem("BBB.IS", skor=70)],
        yapilandirma=risk_ayarlari(
            maksimum_es_zamanli_pozisyon=1,
            pozisyon_basina_sermaye_orani=1.0,
            toplam_acik_risk_orani=0.05,
        ),
    )

    assert rapor.tamamlanan_islem_sayisi == 1
    assert rapor.atlanan_islemler[0].neden == PORTFOY_KAPASITE_NEDENI


def test_islem_maliyeti_stop_riskine_dahil_edilir() -> None:
    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri={"AAA.IS": fiyat_verisi([100, 100, 110])},
        islemler=[islem("AAA.IS")],
        yapilandirma=risk_ayarlari(islem_maliyeti_orani=0.001),
    )

    kayit = rapor.kabul_edilen_islemler[0]
    assert kayit.ayrilan_sermaye < 20_000.0
    assert kayit.planlanan_risk_tutari == pytest.approx(1_000.0)


def test_sabit_mod_mevcut_sermaye_dagilimini_korur() -> None:
    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri={"AAA.IS": fiyat_verisi([100, 100, 110])},
        islemler=[islem("AAA.IS")],
        yapilandirma=PortfolioBacktestConfig(
            baslangic_sermayesi=100_000,
            maksimum_es_zamanli_pozisyon=3,
            pozisyon_basina_sermaye_orani=1 / 3,
            islem_maliyeti_orani=0.0,
            boyutlandirma_modu=BOYUTLANDIRMA_SABIT,
            zarar_durdur_orani=0.05,
        ),
    )

    kayit = rapor.kabul_edilen_islemler[0]
    assert kayit.ayrilan_sermaye == pytest.approx(100_000 / 3)
    assert kayit.planlanan_risk_tutari == pytest.approx(100_000 / 3 * 0.05)


def test_gunluk_rapor_acik_planlanan_riski_gosterir() -> None:
    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri={"AAA.IS": fiyat_verisi([100, 100, 100])},
        islemler=[islem("AAA.IS", cikis=100)],
        yapilandirma=risk_ayarlari(),
    )

    giris_noktasi = rapor.gunluk_noktalar[0]
    assert giris_noktasi.acik_risk_tutari == pytest.approx(1_000.0)
    assert giris_noktasi.acik_risk_orani == pytest.approx(0.01)
    assert rapor.maksimum_acik_risk_orani == pytest.approx(0.01)


def test_karsilastirma_ayni_aday_havuzunu_iki_modda_calistirir() -> None:
    veriler = {
        "AAA.IS": fiyat_verisi([100, 100, 110]),
        "BBB.IS": fiyat_verisi([100, 100, 110]),
        "CCC.IS": fiyat_verisi([100, 100, 110]),
    }
    islemler = [islem("AAA.IS", skor=80), islem("BBB.IS", skor=70), islem("CCC.IS")]

    rapor = PortfolioRiskComparisonAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=islemler,
        islem_maliyeti_orani=0.0,
    )

    assert rapor.sabit.rapor.tamamlanan_islem_sayisi == 3
    assert rapor.risk_bazli.rapor.tamamlanan_islem_sayisi == 2
    assert rapor.risk_bazli.rapor.atlanan_islem_sayisi == 1


def test_karsilastirma_atlanma_nedenlerini_ozetler() -> None:
    veriler = {
        "AAA.IS": fiyat_verisi([100, 100, 110]),
        "BBB.IS": fiyat_verisi([100, 100, 110]),
        "CCC.IS": fiyat_verisi([100, 100, 110]),
    }
    rapor = PortfolioRiskComparisonAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=[islem("AAA.IS", skor=80), islem("BBB.IS", skor=70), islem("CCC.IS")],
        islem_maliyeti_orani=0.0,
    )

    assert rapor.risk_bazli.atlanma_nedenleri == (
        (PORTFOY_RISK_LIMITI_NEDENI, 1),
    )



def test_giris_risk_limiti_kullanimi_yuzde_yuzu_asmaz() -> None:
    veriler = {
        "AAA.IS": fiyat_verisi([100, 100, 110]),
        "BBB.IS": fiyat_verisi([100, 100, 110]),
    }
    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri=veriler,
        islemler=[islem("AAA.IS", skor=80), islem("BBB.IS", skor=70)],
        yapilandirma=risk_ayarlari(),
    )

    assert rapor.maksimum_giris_risk_limiti_kullanim_orani == pytest.approx(1.0)
    assert rapor.maksimum_giris_risk_limiti_kullanim_orani <= 1.0 + 1e-12


def test_gunluk_risk_orani_ozsermaye_dususunde_limiti_gecebilir_ama_giris_limiti_asmaz() -> None:
    veri = fiyat_verisi([100, 100, 90, 100])
    rapor = PortfolioBacktestAnalyzer().analiz_et(
        fiyat_verileri={"AAA.IS": veri, "BBB.IS": veri},
        islemler=[
            islem("AAA.IS", giris_gunu=1, cikis_gunu=3, cikis=100, skor=80),
            islem("BBB.IS", giris_gunu=1, cikis_gunu=3, cikis=100, skor=70),
        ],
        yapilandirma=risk_ayarlari(),
    )

    assert rapor.maksimum_acik_risk_orani > 0.02
    assert rapor.maksimum_giris_risk_limiti_kullanim_orani == pytest.approx(1.0)
