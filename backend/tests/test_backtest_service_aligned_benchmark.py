from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from backend.app.backtest.backtest_models import (
    BacktestConfig,
)
from backend.app.backtest.backtest_service import (
    BacktestServiceConfig,
    StockBacktestService,
)
from backend.app.backtest.historical_signal_generator import (
    HistoricalSignalGeneratorConfig,
)


POZITIF = "Pozitif Teknik Görünüm"


def fiyat_verisi_olustur(
    bar_sayisi: int = 75,
) -> pd.DataFrame:
    acilislar = [
        100.0 + konum * 0.25
        for konum in range(bar_sayisi)
    ]

    return pd.DataFrame(
        {
            "Open": acilislar,
            "High": [
                fiyat + 1.0
                for fiyat in acilislar
            ],
            "Low": [
                fiyat - 1.0
                for fiyat in acilislar
            ],
            "Close": [
                fiyat + 0.50
                for fiyat in acilislar
            ],
            "Volume": [
                1_000_000.0
                for _ in range(bar_sayisi)
            ],
        },
        index=pd.date_range(
            start="2026-01-01",
            periods=bar_sayisi,
            freq="B",
        ),
    )


class OrnekAnalizci:
    def __init__(
        self,
        skor: int = 70,
    ) -> None:
        self.skor = skor

    def veriden_analiz_et(
        self,
        sembol: str,
        fiyat_verisi: pd.DataFrame,
    ) -> object:
        return SimpleNamespace(
            sinyal=SimpleNamespace(
                skor=self.skor,
                karar=POZITIF,
            )
        )


def yapilandirma_olustur() -> BacktestServiceConfig:
    return BacktestServiceConfig(
        islem_gunu=75,
        indirme_donemi="1y",
        pozisyon_cakismalarini_engelle=True,
        sinyal_ayarlari=(
            HistoricalSignalGeneratorConfig(
                minimum_bar_sayisi=60
            )
        ),
        backtest_ayarlari=BacktestConfig(
            elde_tutma_gunu=2,
            minimum_skor=50,
            baslangic_sermayesi=100_000.0,
            pozisyon_orani=1.0,
            islem_maliyeti_orani=0.0,
        ),
    )


def test_hizalanmis_benchmark_ilk_giris_ve_son_cikisa_gore_hesaplanir() -> None:
    servis = StockBacktestService(
        veri_getirici=lambda **kwargs: (
            fiyat_verisi_olustur()
        ),
        analizci=OrnekAnalizci(),
    )

    rapor = servis.calistir(
        sembol="AAA",
        yapilandirma=yapilandirma_olustur(),
    )

    islemler = rapor.backtest_sonucu.islemler

    assert islemler

    ilk_giris_tarihi = min(
        islem.giris_tarihi
        for islem in islemler
    )

    son_cikis_tarihi = max(
        islem.cikis_tarihi
        for islem in islemler
    )

    hizalanmis = (
        rapor
        .hizalanmis_benchmark_karsilastirmasi
    )

    assert hizalanmis is not None

    assert (
        hizalanmis.al_tut.baslangic_tarihi
        == ilk_giris_tarihi
    )

    assert (
        hizalanmis.al_tut.bitis_tarihi
        == son_cikis_tarihi
    )

    assert (
        rapor.benchmark_karsilastirmasi
        .al_tut.baslangic_tarihi.isoformat()
        == rapor.ilk_fiyat_tarihi
    )

    assert (
        hizalanmis.al_tut.takvim_gunu_sayisi
        < rapor.benchmark_karsilastirmasi
        .al_tut.takvim_gunu_sayisi
    )


def test_islem_yoksa_hizalanmis_benchmark_uretilmez() -> None:
    servis = StockBacktestService(
        veri_getirici=lambda **kwargs: (
            fiyat_verisi_olustur()
        ),
        analizci=OrnekAnalizci(
            skor=40
        ),
    )

    rapor = servis.calistir(
        sembol="AAA.IS",
        yapilandirma=yapilandirma_olustur(),
    )

    assert rapor.tamamlanan_islem_sayisi == 0

    assert (
        rapor
        .hizalanmis_benchmark_karsilastirmasi
        is None
    )

    assert (
        rapor.benchmark_karsilastirmasi
        is not None
    )