from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from backend.app.backtest.backtest_models import (
    BacktestConfig,
)
from backend.app.backtest.backtest_service import (
    BacktestServiceConfig,
    BacktestServiceError,
    StockBacktestService,
)
from backend.app.backtest.historical_signal_generator import (
    HistoricalSignalGeneratorConfig,
)
from backend.app.backtest.position_overlap import (
    CAKISMA_NEDENI,
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
                + konum * 10_000
                for konum in range(bar_sayisi)
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
        self.gorulen_uzunluklar: list[int] = []

    def veriden_analiz_et(
        self,
        sembol: str,
        fiyat_verisi: pd.DataFrame,
    ) -> object:
        self.gorulen_uzunluklar.append(
            len(fiyat_verisi)
        )

        return SimpleNamespace(
            sinyal=SimpleNamespace(
                skor=self.skor,
                karar=POZITIF,
            )
        )


def test_servis_veriyi_indirip_cakismasiz_backtest_calistirir() -> None:
    fiyat_verisi = fiyat_verisi_olustur()
    gelen_argumanlar: dict[str, object] = {}

    def veri_getirici(
        sembol: str,
        islem_gunu: int,
        indirme_donemi: str,
        yalnizca_tamamlanmis_gunler: bool,
    ) -> pd.DataFrame:
        gelen_argumanlar.update(
            {
                "sembol": sembol,
                "islem_gunu": islem_gunu,
                "indirme_donemi": indirme_donemi,
                "tamamlanmis": (
                    yalnizca_tamamlanmis_gunler
                ),
            }
        )

        return fiyat_verisi

    analizci = OrnekAnalizci()

    servis = StockBacktestService(
        veri_getirici=veri_getirici,
        analizci=analizci,
    )

    rapor = servis.calistir(
        sembol=" thyao ",
        yapilandirma=BacktestServiceConfig(
            islem_gunu=500,
            indirme_donemi="2y",
            pozisyon_cakismalarini_engelle=True,
            sinyal_ayarlari=(
                HistoricalSignalGeneratorConfig(
                    minimum_bar_sayisi=60
                )
            ),
            backtest_ayarlari=BacktestConfig(
                elde_tutma_gunu=2,
                minimum_skor=50,
                islem_maliyeti_orani=0.0,
            ),
        ),
    )

    assert gelen_argumanlar == {
        "sembol": "THYAO.IS",
        "islem_gunu": 500,
        "indirme_donemi": "2y",
        "tamamlanmis": True,
    }

    assert rapor.sembol == "THYAO.IS"
    assert rapor.fiyat_bar_sayisi == 65
    assert rapor.ilk_fiyat_tarihi == "2026-01-01"
    assert rapor.son_fiyat_tarihi == "2026-04-01"

    assert rapor.uretilen_sinyal_sayisi == 5
    assert rapor.tamamlanan_islem_sayisi == 3

    assert (
        rapor.cakisma_nedeniyle_atlanan_sinyal_sayisi
        == 2
    )

    assert all(
        CAKISMA_NEDENI in atlanan.neden
        for atlanan
        in rapor.backtest_sonucu.atlanan_sinyaller
    )

    assert analizci.gorulen_uzunluklar == [
        60,
        61,
        62,
        63,
        64,
    ]


def test_dusuk_skorlu_sinyaller_motor_tarafindan_atlanir() -> None:
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
            sinyal_ayarlari=(
                HistoricalSignalGeneratorConfig(
                    minimum_bar_sayisi=60
                )
            ),
            backtest_ayarlari=BacktestConfig(
                minimum_skor=50,
                islem_maliyeti_orani=0.0,
            ),
        ),
    )

    assert rapor.uretilen_sinyal_sayisi == 5
    assert rapor.tamamlanan_islem_sayisi == 0

    assert (
        rapor.backtest_sonucu.atlanan_sinyal_sayisi
        == 5
    )

    assert (
        rapor.cakisma_nedeniyle_atlanan_sinyal_sayisi
        == 0
    )

    assert all(
        "minimum 50" in atlanan.neden
        for atlanan
        in rapor.backtest_sonucu.atlanan_sinyaller
    )


def test_bos_fiyat_verisi_hata_verir() -> None:
    servis = StockBacktestService(
        veri_getirici=lambda **kwargs: pd.DataFrame(),
        analizci=OrnekAnalizci(),
    )

    with pytest.raises(
        BacktestServiceError,
        match="fiyat verisi bulunamadı",
    ):
        servis.calistir(
            sembol="AAA.IS"
        )


def test_veri_getirici_hatasi_servis_hatasina_donusturulur() -> None:
    def hatali_veri_getirici(
        **kwargs: object,
    ) -> pd.DataFrame:
        raise ValueError(
            "Örnek veri indirme hatası"
        )

    servis = StockBacktestService(
        veri_getirici=hatali_veri_getirici,
        analizci=OrnekAnalizci(),
    )

    with pytest.raises(
        BacktestServiceError,
        match="Örnek veri indirme hatası",
    ):
        servis.calistir(
            sembol="AAA.IS"
        )


def test_gecersiz_servis_ayarlari_hata_verir() -> None:
    with pytest.raises(
        ValueError,
        match="İşlem günü",
    ):
        BacktestServiceConfig(
            islem_gunu=0
        )

    with pytest.raises(
        ValueError,
        match="İndirme dönemi",
    ):
        BacktestServiceConfig(
            indirme_donemi=" "
        )

    with pytest.raises(
        ValueError,
        match="Geçersiz indirme dönemi",
    ):
        BacktestServiceConfig(
            indirme_donemi="3y"
        )

    with pytest.raises(
        ValueError,
        match="Pozisyon çakışma",
    ):
        BacktestServiceConfig(
            pozisyon_cakismalarini_engelle=(
                "evet"  # type: ignore[arg-type]
            )
        )

    with pytest.raises(
        TypeError,
        match="çağrılabilir",
    ):
        StockBacktestService(
            veri_getirici="geçersiz",  # type: ignore[arg-type]
        )