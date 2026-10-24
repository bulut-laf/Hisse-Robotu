from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from backend.app.backtest.analysis_context import analiz_baglamini_olustur
from backend.app.backtest.analysis_profile import AnalysisProfile
from backend.app.backtest.backtest_service import (
    BacktestServiceConfig,
    StockBacktestService,
)


POZITIF = "Pozitif Teknik Görünüm"


def fiyat_verisi_olustur() -> pd.DataFrame:
    tarihler = pd.date_range("2026-01-01", periods=65, freq="B")
    acilislar = [100.0 + konum * 0.25 for konum in range(65)]

    return pd.DataFrame(
        {
            "Open": acilislar,
            "High": [fiyat + 1.0 for fiyat in acilislar],
            "Low": [fiyat - 1.0 for fiyat in acilislar],
            "Close": [fiyat + 0.5 for fiyat in acilislar],
            "Volume": [1_000_000.0 for _ in acilislar],
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


def test_baglam_tarih_bar_ve_kimlikleri_uretir() -> None:
    veri = fiyat_verisi_olustur()
    profil = AnalysisProfile(islem_gunu=65, indirme_donemi="1y")

    baglam = analiz_baglamini_olustur(veri, profil)

    assert baglam.ilk_tarih.isoformat() == "2026-01-01"
    assert baglam.son_tarih == veri.index[-1].date()
    assert baglam.fiyat_bar_sayisi == 65
    assert len(baglam.veri_kimligi) == 12
    assert len(baglam.analiz_kimligi) == 12


def test_ayni_veri_ve_ayarlar_ayni_analiz_kimligini_uretir() -> None:
    veri = fiyat_verisi_olustur()
    profil = AnalysisProfile(islem_gunu=65, indirme_donemi="1y")

    birinci = analiz_baglamini_olustur(veri, profil)
    ikinci = analiz_baglamini_olustur(veri.copy(), profil)

    assert birinci.veri_kimligi == ikinci.veri_kimligi
    assert birinci.analiz_kimligi == ikinci.analiz_kimligi


def test_fiyat_degisikligi_veri_ve_analiz_kimligini_degistirir() -> None:
    veri = fiyat_verisi_olustur()
    degisen = veri.copy()
    degisen.loc[degisen.index[-1], "Close"] += 1.0
    profil = AnalysisProfile(islem_gunu=65, indirme_donemi="1y")

    birinci = analiz_baglamini_olustur(veri, profil)
    ikinci = analiz_baglamini_olustur(degisen, profil)

    assert birinci.veri_kimligi != ikinci.veri_kimligi
    assert birinci.analiz_kimligi != ikinci.analiz_kimligi


def test_backtest_servisi_rapora_analiz_baglamini_ekler() -> None:
    veri = fiyat_verisi_olustur()
    profil = AnalysisProfile(islem_gunu=65, indirme_donemi="1y")
    servis = StockBacktestService(
        veri_getirici=lambda **kwargs: veri,
        analizci=OrnekAnalizci(),
    )

    rapor = servis.calistir(
        sembol="AAA",
        yapilandirma=BacktestServiceConfig(
            islem_gunu=profil.islem_gunu,
            indirme_donemi=profil.indirme_donemi,
            sinyal_ayarlari=profil.sinyal_yapilandirmasi(),
            backtest_ayarlari=profil.backtest_yapilandirmasi(),
        ),
    )

    assert rapor.analiz_baglami is not None
    assert rapor.analiz_baglami.fiyat_bar_sayisi == 65
    assert rapor.analiz_baglami.ayar_kimligi == profil.ayar_kimligi
