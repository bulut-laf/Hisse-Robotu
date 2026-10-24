from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

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
    bar_sayisi: int = 65,
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


def test_servis_al_tut_karsilastirmasini_rapora_ekler() -> None:
    servis = StockBacktestService(
        veri_getirici=lambda **kwargs: (
            fiyat_verisi_olustur()
        ),
        analizci=OrnekAnalizci(),
    )

    rapor = servis.calistir(
        sembol="AAA",
        yapilandirma=BacktestServiceConfig(
            islem_gunu=65,
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
        ),
    )

    benchmark = rapor.benchmark_karsilastirmasi
    al_tut = benchmark.al_tut
    karsilastirma = benchmark.karsilastirma
    ozsermaye = rapor.ozsermaye_raporu

    assert al_tut.baslangic_tarihi.isoformat() == (
        rapor.ilk_fiyat_tarihi
    )

    assert al_tut.bitis_tarihi.isoformat() == (
        rapor.son_fiyat_tarihi
    )

    assert al_tut.giris_fiyati == 100.0
    assert al_tut.cikis_fiyati == 116.5

    assert (
        al_tut.net_getiri_orani
        == pytest.approx(0.165)
    )

    assert (
        al_tut.bitis_sermayesi
        == pytest.approx(116_500.0)
    )

    assert (
        karsilastirma
        .strateji_toplam_getiri_orani
        == pytest.approx(
            ozsermaye
            .toplam_bilesik_getiri_orani
        )
    )

    assert (
        karsilastirma
        .strateji_maksimum_dusus_orani
        == pytest.approx(
            ozsermaye
            .maksimum_dusus_orani
        )
    )

    assert (
        karsilastirma
        .al_tut_toplam_getiri_orani
        == pytest.approx(
            al_tut.net_getiri_orani
        )
    )

    assert (
        karsilastirma.toplam_getiri_lideri
        == "Al-Tut"
    )


def test_islem_olmasa_da_al_tut_karsilastirmasi_uretilir() -> None:
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
        yapilandirma=BacktestServiceConfig(
            islem_gunu=65,
            indirme_donemi="1y",
            sinyal_ayarlari=(
                HistoricalSignalGeneratorConfig(
                    minimum_bar_sayisi=60
                )
            ),
            backtest_ayarlari=BacktestConfig(
                minimum_skor=50,
                baslangic_sermayesi=100_000.0,
                pozisyon_orani=1.0,
                islem_maliyeti_orani=0.0,
            ),
        ),
    )

    benchmark = rapor.benchmark_karsilastirmasi
    karsilastirma = benchmark.karsilastirma

    assert rapor.tamamlanan_islem_sayisi == 0

    assert (
        karsilastirma
        .strateji_toplam_getiri_orani
        == 0.0
    )

    assert (
        karsilastirma
        .strateji_maksimum_dusus_orani
        == 0.0
    )

    assert (
        benchmark.al_tut.net_getiri_orani
        > 0.0
    )

    assert (
        karsilastirma.toplam_getiri_lideri
        == "Al-Tut"
    )