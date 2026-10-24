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


def test_servis_ozsermaye_raporunu_ekler() -> None:
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

    ozsermaye = rapor.ozsermaye_raporu
    metrikler = rapor.backtest_sonucu.metrikler
    dagilim = rapor.performans_dagilimi

    assert rapor.tamamlanan_islem_sayisi == 3
    assert ozsermaye.islem_sayisi == 3
    assert len(ozsermaye.noktalar) == 3

    assert (
        ozsermaye.bitis_sermayesi
        == pytest.approx(
            metrikler.bitis_sermayesi
        )
    )

    assert (
        ozsermaye.bitis_sermayesi
        == pytest.approx(
            dagilim.bitis_sermayesi
        )
    )

    assert (
        ozsermaye.toplam_bilesik_getiri_orani
        == pytest.approx(
            metrikler
            .toplam_net_getiri_orani
        )
    )

    assert (
        ozsermaye.toplam_bilesik_getiri_orani
        == pytest.approx(
            dagilim
            .toplam_bilesik_getiri_orani
        )
    )

    assert all(
        nokta.sonraki_sermaye > 0
        for nokta in ozsermaye.noktalar
    )

    assert (
        ozsermaye.maksimum_dusus_orani
        >= 0.0
    )


def test_islem_yoksa_ozsermaye_raporu_bos_olur() -> None:
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

    ozsermaye = rapor.ozsermaye_raporu

    assert rapor.tamamlanan_islem_sayisi == 0
    assert ozsermaye.islem_sayisi == 0
    assert ozsermaye.dusus_donemi_sayisi == 0
    assert ozsermaye.noktalar == ()
    assert ozsermaye.dusus_donemleri == ()
    assert ozsermaye.maksimum_dusus_orani == 0.0
    assert ozsermaye.maksimum_dusus_donemi is None
    assert ozsermaye.en_uzun_dusus_donemi is None

    assert (
        ozsermaye.bitis_sermayesi
        == pytest.approx(100_000.0)
    )

    assert (
        ozsermaye.toplam_bilesik_getiri_orani
        == 0.0
    )