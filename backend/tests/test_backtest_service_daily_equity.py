from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from backend.app.backtest.backtest_engine import BacktestResult
from backend.app.backtest.backtest_models import (
    BacktestConfig,
    BacktestMetrics,
    BacktestTrade,
    CIKIS_SURE_SONU,
)
from backend.app.backtest.backtest_service import (
    BacktestServiceConfig,
    StockBacktestService,
)
from backend.app.backtest.historical_signal_generator import (
    HistoricalSignalGeneratorConfig,
)


POZITIF = "Pozitif Teknik Görünüm"


def fiyat_verisi_olustur() -> pd.DataFrame:
    tarihler = pd.date_range(
        start="2026-01-01",
        periods=65,
        freq="B",
    )

    kapanislar = [100.0 for _ in tarihler]
    kapanislar[61] = 50.0
    kapanislar[62] = 80.0
    kapanislar[63] = 100.0
    kapanislar[64] = 110.0

    return pd.DataFrame(
        {
            "Open": [100.0 for _ in tarihler],
            "High": [112.0 for _ in tarihler],
            "Low": [45.0 for _ in tarihler],
            "Close": kapanislar,
            "Volume": [1_000_000.0 for _ in tarihler],
        },
        index=tarihler,
    )


class OrnekAnalizci:
    def veriden_analiz_et(
        self,
        sembol: str,
        fiyat_verisi: pd.DataFrame,
    ) -> object:
        return SimpleNamespace(
            sinyal=SimpleNamespace(
                skor=70,
                karar=POZITIF,
            )
        )


class SabitBacktestMotoru:
    def __init__(
        self,
        fiyat_verisi: pd.DataFrame,
    ) -> None:
        self._fiyat_verisi = fiyat_verisi

    def calistir(
        self,
        veriler: object,
        sinyaller: object,
        yapilandirma: BacktestConfig,
    ) -> BacktestResult:
        tarihler = self._fiyat_verisi.index

        islem = BacktestTrade.olustur(
            sembol="AAA.IS",
            sinyal_tarihi=tarihler[59].date(),
            giris_tarihi=tarihler[60].date(),
            cikis_tarihi=tarihler[64].date(),
            giris_fiyati=100.0,
            cikis_fiyati=110.0,
            skor=70,
            teknik_gorunum=POZITIF,
            elde_tutulan_bar=5,
            cikis_nedeni=CIKIS_SURE_SONU,
            islem_maliyeti_orani=(
                yapilandirma.islem_maliyeti_orani
            ),
        )

        islemler = (islem,)

        return BacktestResult(
            islemler=islemler,
            atlanan_sinyaller=(),
            metrikler=BacktestMetrics.hesapla(
                islemler=islemler,
                yapilandirma=yapilandirma,
            ),
        )


def yapilandirma_olustur(
    cakisma_filtresi: bool,
) -> BacktestServiceConfig:
    return BacktestServiceConfig(
        islem_gunu=65,
        indirme_donemi="1y",
        pozisyon_cakismalarini_engelle=(
            cakisma_filtresi
        ),
        sinyal_ayarlari=HistoricalSignalGeneratorConfig(
            minimum_bar_sayisi=60,
        ),
        backtest_ayarlari=BacktestConfig(
            elde_tutma_gunu=5,
            minimum_skor=50,
            baslangic_sermayesi=100_000.0,
            pozisyon_orani=1.0,
            islem_maliyeti_orani=0.0,
        ),
    )


def test_servis_gunluk_ozsermaye_raporunu_ekler() -> None:
    fiyat_verisi = fiyat_verisi_olustur()

    servis = StockBacktestService(
        veri_getirici=lambda **kwargs: fiyat_verisi,
        analizci=OrnekAnalizci(),
        backtest_motoru=SabitBacktestMotoru(
            fiyat_verisi
        ),
    )

    rapor = servis.calistir(
        sembol="AAA",
        yapilandirma=yapilandirma_olustur(
            cakisma_filtresi=True
        ),
    )

    gunluk = rapor.gunluk_ozsermaye_raporu

    assert gunluk is not None
    assert gunluk.islem_gunu_sayisi == 5
    assert gunluk.bitis_sermayesi == pytest.approx(110_000.0)
    assert gunluk.maksimum_dusus_orani == pytest.approx(0.50)

    assert rapor.ozsermaye_raporu.maksimum_dusus_orani == 0.0

    hizalanmis = rapor.hizalanmis_benchmark_karsilastirmasi

    assert hizalanmis is not None
    assert (
        hizalanmis.karsilastirma
        .strateji_maksimum_dusus_orani
        == pytest.approx(0.50)
    )


def test_cakisma_filtresi_kapaliyken_gunluk_rapor_atlanir() -> None:
    fiyat_verisi = fiyat_verisi_olustur()

    servis = StockBacktestService(
        veri_getirici=lambda **kwargs: fiyat_verisi,
        analizci=OrnekAnalizci(),
        backtest_motoru=SabitBacktestMotoru(
            fiyat_verisi
        ),
    )

    rapor = servis.calistir(
        sembol="AAA.IS",
        yapilandirma=yapilandirma_olustur(
            cakisma_filtresi=False
        ),
    )

    assert rapor.gunluk_ozsermaye_raporu is None

    hizalanmis = rapor.hizalanmis_benchmark_karsilastirmasi

    assert hizalanmis is not None
    assert (
        hizalanmis.karsilastirma
        .strateji_maksimum_dusus_orani
        == rapor.ozsermaye_raporu.maksimum_dusus_orani
    )
