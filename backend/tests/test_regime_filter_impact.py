from __future__ import annotations

import pandas as pd
import pytest

from backend.app.backtest.backtest_models import BacktestConfig, BacktestSignal
from backend.app.backtest.market_regime_analysis import MarketRegimeConfig
from backend.app.backtest.regime_filter_impact import (
    RegimeFilterImpactAnalyzer,
    RegimeFilterImpactError,
)
from backend.app.backtest.rolling_window_analysis import RollingWindowConfig


GORUNUM = "Pozitif Teknik Görünüm"


def fiyat_verisi_olustur() -> pd.DataFrame:
    kapanislar = (
        [100.0 + i for i in range(18)]
        + [118.0 - i for i in range(10)]
        + [108.0 + i * 0.8 for i in range(18)]
    )
    return pd.DataFrame(
        {
            "Open": kapanislar,
            "High": [f + 1.0 for f in kapanislar],
            "Low": [f - 1.0 for f in kapanislar],
            "Close": kapanislar,
            "Volume": [1_000_000.0 for _ in kapanislar],
        },
        index=pd.date_range("2026-01-01", periods=len(kapanislar), freq="D"),
    )


def sinyaller_olustur(fiyatlar: pd.DataFrame) -> tuple[BacktestSignal, ...]:
    return tuple(
        BacktestSignal(
            sembol="AAA.IS",
            sinyal_tarihi=fiyatlar.index[i].date(),
            skor=60,
            teknik_gorunum=GORUNUM,
        )
        for i in (8, 12, 20, 24, 32, 38)
    )


def backtest_ayari() -> BacktestConfig:
    return BacktestConfig(
        elde_tutma_gunu=2,
        minimum_skor=50,
        baslangic_sermayesi=100_000.0,
        pozisyon_orani=1.0,
        islem_maliyeti_orani=0.0,
        zarar_durdur_orani=None,
        hedef_orani=None,
    )


def rejim_ayari() -> MarketRegimeConfig:
    return MarketRegimeConfig(
        hizli_ema_periyodu=2,
        yavas_ema_periyodu=4,
        egim_bakisi=1,
        minimum_ema_farki_orani=0.001,
        atr_periyodu=2,
        volatilite_bakisi=3,
        yuksek_volatilite_carpani=1.0,
    )


def pencere_ayari() -> RollingWindowConfig:
    return RollingWindowConfig(
        pencere_bar_sayisi=18,
        adim_bar_sayisi=9,
        minimum_islem_sayisi=1,
    )


def analiz_et():
    fiyatlar = fiyat_verisi_olustur()
    return RegimeFilterImpactAnalyzer().analiz_et(
        sembol="AAA",
        fiyat_verisi=fiyatlar,
        sinyaller=sinyaller_olustur(fiyatlar),
        backtest_yapilandirmasi=backtest_ayari(),
        rejim_yapilandirmasi=rejim_ayari(),
        kayan_pencere_yapilandirmasi=pencere_ayari(),
    )


def test_yalnizca_yukselis_rejimi_sinyalleri_filtreye_alinir() -> None:
    rapor = analiz_et()

    assert rapor.toplam_sinyal_sayisi == 6
    assert rapor.rejimi_belirlenen_sinyal_sayisi == 6
    assert 0 < rapor.filtreye_uygun_sinyal_sayisi < 6
    assert rapor.filtre_disi_sinyal_sayisi == (
        rapor.rejimi_belirlenen_sinyal_sayisi
        - rapor.filtreye_uygun_sinyal_sayisi
    )


def test_baz_ve_filtreli_metrikler_ayri_uretilir() -> None:
    rapor = analiz_et()

    assert rapor.baz.ad == "Baz Strateji"
    assert rapor.filtreli.ad == "Yalnızca Yükseliş Trendi"
    assert rapor.baz.sinyal_sayisi == 6
    assert rapor.filtreli.sinyal_sayisi == rapor.filtreye_uygun_sinyal_sayisi
    assert rapor.baz.islem_sayisi >= rapor.filtreli.islem_sayisi


def test_fark_alanlari_metriklerle_tutarlidir() -> None:
    rapor = analiz_et()

    assert rapor.toplam_getiri_farki_orani == pytest.approx(
        rapor.filtreli.toplam_getiri_orani - rapor.baz.toplam_getiri_orani
    )
    assert rapor.yillik_getiri_farki_orani == pytest.approx(
        rapor.filtreli.yilliklandirilmis_getiri_orani
        - rapor.baz.yilliklandirilmis_getiri_orani
    )
    assert rapor.maksimum_dusus_farki_orani == pytest.approx(
        rapor.filtreli.maksimum_dusus_orani
        - rapor.baz.maksimum_dusus_orani
    )


def test_kayan_pencere_raporlari_ayni_donemleri_kullanir() -> None:
    rapor = analiz_et()

    assert rapor.baz_kayan_pencere.pencere_sayisi == (
        rapor.filtreli_kayan_pencere.pencere_sayisi
    )
    assert [
        (p.baslangic_tarihi, p.bitis_tarihi)
        for p in rapor.baz_kayan_pencere.pencereler
    ] == [
        (p.baslangic_tarihi, p.bitis_tarihi)
        for p in rapor.filtreli_kayan_pencere.pencereler
    ]


def test_kayan_pencere_ozeti_eslesmis_pencereleri_sayar() -> None:
    rapor = analiz_et()
    ozet = rapor.kayan_pencere_ozeti

    assert ozet.toplam_eslesmis_pencere >= 1
    assert (
        ozet.filtre_ustun_pencere
        + ozet.baz_ustun_pencere
        + ozet.esit_pencere
        == ozet.toplam_eslesmis_pencere
    )
    assert 0 <= ozet.filtre_ustunluk_orani <= 1


def test_getiri_dusus_orani_sifir_dususte_none_olabilir() -> None:
    rapor = analiz_et()

    for metrik in (rapor.baz, rapor.filtreli):
        if metrik.maksimum_dusus_orani == 0:
            assert metrik.getiri_dusus_orani is None
        else:
            assert metrik.getiri_dusus_orani == pytest.approx(
                metrik.toplam_getiri_orani / metrik.maksimum_dusus_orani
            )


def test_bos_sembol_hata_verir() -> None:
    fiyatlar = fiyat_verisi_olustur()

    with pytest.raises(RegimeFilterImpactError, match="boş olamaz"):
        RegimeFilterImpactAnalyzer().analiz_et(
            sembol=" ",
            fiyat_verisi=fiyatlar,
            sinyaller=(),
            backtest_yapilandirmasi=backtest_ayari(),
            rejim_yapilandirmasi=rejim_ayari(),
            kayan_pencere_yapilandirmasi=pencere_ayari(),
        )


def test_farkli_sembol_sinyalleri_hesaba_katilmaz() -> None:
    fiyatlar = fiyat_verisi_olustur()
    yabanci = BacktestSignal(
        sembol="BBB.IS",
        sinyal_tarihi=fiyatlar.index[10].date(),
        skor=60,
        teknik_gorunum=GORUNUM,
    )
    rapor = RegimeFilterImpactAnalyzer().analiz_et(
        sembol="AAA.IS",
        fiyat_verisi=fiyatlar,
        sinyaller=sinyaller_olustur(fiyatlar) + (yabanci,),
        backtest_yapilandirmasi=backtest_ayari(),
        rejim_yapilandirmasi=rejim_ayari(),
        kayan_pencere_yapilandirmasi=pencere_ayari(),
    )

    assert rapor.toplam_sinyal_sayisi == 6
