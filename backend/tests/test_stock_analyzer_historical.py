from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

import backend.app.analysis.stock_analyzer as stock_analyzer_modulu
from backend.app.analysis.stock_analyzer import (
    StockAnalyzer,
    StockAnalyzerError,
)
from backend.app.backtest.historical_signal_generator import (
    HistoricalSignalGenerator,
    HistoricalSignalGeneratorConfig,
)


def fiyat_verisi_olustur(
    bar_sayisi: int = 6,
) -> pd.DataFrame:
    acilislar = [
        100.0 + konum
        for konum in range(bar_sayisi)
    ]

    return pd.DataFrame(
        {
            "Open": acilislar,
            "High": [
                fiyat + 2.0
                for fiyat in acilislar
            ],
            "Low": [
                fiyat - 2.0
                for fiyat in acilislar
            ],
            "Close": [
                fiyat + 1.0
                for fiyat in acilislar
            ],
            "Volume": [
                1_000_000 + konum * 10_000
                for konum in range(bar_sayisi)
            ],
        },
        index=pd.date_range(
            start="2026-01-01",
            periods=bar_sayisi,
            freq="D",
        ),
    )


def analiz_bagimliliklarini_hazirla(
    monkeypatch: pytest.MonkeyPatch,
    gorulen_uzunluklar: list[int] | None = None,
) -> None:
    def teknik_gostergeleri_ekle(
        veri: pd.DataFrame,
    ) -> pd.DataFrame:
        if gorulen_uzunluklar is not None:
            gorulen_uzunluklar.append(
                len(veri)
            )

        sonuc = veri.copy()

        sonuc["EMA9"] = sonuc["Close"] - 1.0
        sonuc["EMA21"] = sonuc["Close"] - 2.0
        sonuc["RSI14"] = 60.0
        sonuc["MACD"] = 1.0
        sonuc["MACD_Sinyal"] = 0.50
        sonuc["MACD_Histogram"] = 0.50
        sonuc["ATR14"] = 2.0
        sonuc["ATR_Yuzde"] = (
            sonuc["ATR14"]
            / sonuc["Close"]
            * 100
        )

        return sonuc

    def hacim_gostergelerini_ekle(
        veri: pd.DataFrame,
        ortalama_periyodu: int,
        patlama_esigi: float,
    ) -> pd.DataFrame:
        assert ortalama_periyodu == 20
        assert patlama_esigi == pytest.approx(
            1.50
        )

        sonuc = veri.copy()

        sonuc["Hacim_Orani"] = 1.25
        sonuc["Fiyat_Hacim_Durumu"] = (
            "Normal Üzeri Hacimli Yükseliş"
        )
        sonuc["Gunluk_Getiri_Yuzde"] = 1.0
        sonuc["Hacim_Patlamasi"] = False
        sonuc["Yukselis_Hacim_Patlamasi"] = False
        sonuc["Dusus_Hacim_Patlamasi"] = False

        return sonuc

    risk_plani = SimpleNamespace(
        risk_odul_orani=2.25,
        filtreyi_gecti=True,
        risk_notu="Orta Volatiliteli",
        hedef_fiyat=115.0,
        stop_fiyat=95.0,
    )

    sinyal = SimpleNamespace(
        skor=72,
        karar="Nötr Teknik Görünüm",
        trend_puani=25,
        momentum_puani=25,
        hacim_puani=12,
        risk_puani=10,
        pozitif_nedenler=(),
        riskler=(),
    )

    monkeypatch.setattr(
        stock_analyzer_modulu,
        "teknik_gostergeleri_ekle",
        teknik_gostergeleri_ekle,
    )

    monkeypatch.setattr(
        stock_analyzer_modulu,
        "hacim_gostergelerini_ekle",
        hacim_gostergelerini_ekle,
    )

    monkeypatch.setattr(
        stock_analyzer_modulu,
        "destek_direnc_bul",
        lambda **kwargs: SimpleNamespace(
            destek=None,
            direnc=None,
        ),
    )

    monkeypatch.setattr(
        stock_analyzer_modulu,
        "risk_plani_olustur",
        lambda **kwargs: risk_plani,
    )

    monkeypatch.setattr(
        stock_analyzer_modulu,
        "sinyal_uret",
        lambda **kwargs: sinyal,
    )


def test_veriden_analiz_et_veri_indirmez(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analiz_bagimliliklarini_hazirla(
        monkeypatch
    )

    def veri_indirilmemeli(
        *args: Any,
        **kwargs: Any,
    ) -> pd.DataFrame:
        raise AssertionError(
            "veriden_analiz_et piyasa verisi indirmemelidir."
        )

    monkeypatch.setattr(
        stock_analyzer_modulu,
        "fiyat_verisi_getir",
        veri_indirilmemeli,
    )

    sonuc = StockAnalyzer().veriden_analiz_et(
        sembol=" aaa.is ",
        fiyat_verisi=fiyat_verisi_olustur(),
    )

    assert sonuc.sembol == "AAA.IS"
    assert sonuc.analiz_tarihi == "2026-01-06"
    assert sonuc.kapanis == pytest.approx(
        106.0
    )
    assert sonuc.sinyal.skor == 72
    assert sonuc.hedef_kaynagi == (
        "ATR tahmini — direnç bulunamadı"
    )


def test_analiz_et_veriyi_indirip_ortak_metodu_kullanir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fiyat_verisi = fiyat_verisi_olustur()

    indirilen_semboller: list[str] = []
    aktarilan_veriler: list[pd.DataFrame] = []

    def veri_getir(
        sembol: str,
        islem_gunu: int,
        indirme_donemi: str,
        yalnizca_tamamlanmis_gunler: bool,
    ) -> pd.DataFrame:
        indirilen_semboller.append(
            sembol
        )

        assert islem_gunu == 160
        assert indirme_donemi == "1y"
        assert yalnizca_tamamlanmis_gunler is True

        return fiyat_verisi

    beklenen_sonuc = SimpleNamespace(
        sembol="AAA.IS"
    )

    def veriden_analiz_et(
        self: StockAnalyzer,
        sembol: str,
        fiyat_verisi: pd.DataFrame,
    ) -> object:
        aktarilan_veriler.append(
            fiyat_verisi
        )

        assert sembol == "AAA.IS"

        return beklenen_sonuc

    monkeypatch.setattr(
        stock_analyzer_modulu,
        "fiyat_verisi_getir",
        veri_getir,
    )

    monkeypatch.setattr(
        StockAnalyzer,
        "veriden_analiz_et",
        veriden_analiz_et,
    )

    sonuc = StockAnalyzer().analiz_et(
        " aaa.is "
    )

    assert sonuc is beklenen_sonuc
    assert indirilen_semboller == [
        "AAA.IS",
    ]
    assert aktarilan_veriler == [
        fiyat_verisi,
    ]


def test_historical_generator_stock_analyzer_metodunu_kullanir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gorulen_uzunluklar: list[int] = []

    analiz_bagimliliklarini_hazirla(
        monkeypatch=monkeypatch,
        gorulen_uzunluklar=gorulen_uzunluklar,
    )

    analyzer = StockAnalyzer()

    generator = HistoricalSignalGenerator(
        analyzer.veriden_analiz_et
    )

    sonuc = generator.uret(
        sembol="AAA.IS",
        fiyat_verisi=fiyat_verisi_olustur(
            bar_sayisi=6
        ),
        yapilandirma=(
            HistoricalSignalGeneratorConfig(
                minimum_bar_sayisi=3
            )
        ),
    )

    assert gorulen_uzunluklar == [
        3,
        4,
        5,
    ]

    assert sonuc.degerlendirilen_gun_sayisi == 3
    assert sonuc.sinyal_sayisi == 3

    assert [
        sinyal.skor
        for sinyal in sonuc.sinyaller
    ] == [
        72,
        72,
        72,
    ]

    assert [
        sinyal.sinyal_tarihi.isoformat()
        for sinyal in sonuc.sinyaller
    ] == [
        "2026-01-03",
        "2026-01-04",
        "2026-01-05",
    ]


def test_veriden_analiz_et_gecersiz_veriyi_reddeder() -> None:
    analyzer = StockAnalyzer()

    with pytest.raises(
        StockAnalyzerError,
        match="DataFrame",
    ):
        analyzer.veriden_analiz_et(
            sembol="AAA.IS",
            fiyat_verisi="geçersiz",  # type: ignore[arg-type]
        )

    with pytest.raises(
        StockAnalyzerError,
        match="boş",
    ):
        analyzer.veriden_analiz_et(
            sembol="AAA.IS",
            fiyat_verisi=pd.DataFrame(),
        )