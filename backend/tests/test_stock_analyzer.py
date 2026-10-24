from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.app.analysis import stock_analyzer as stock_analyzer_module
from backend.app.analysis.stock_analyzer import (
    StockAnalyzer,
    StockAnalyzerError,
)
from backend.app.data.market_data import MarketDataError


def sentetik_piyasa_verisi(
    gun_sayisi: int = 120,
) -> pd.DataFrame:
    """
    İnternet bağlantısına ihtiyaç duymayan sentetik OHLCV verisi üretir.

    Hafif dalgalanan ve genel olarak yükselen fiyat yapısı kullanılır.
    """
    tarihler = pd.bdate_range(
        start="2026-01-02",
        periods=gun_sayisi,
    )

    ana_trend = np.linspace(
        100.0,
        145.0,
        gun_sayisi,
    )

    dalgalanma = np.sin(
        np.linspace(0, 10, gun_sayisi)
    ) * 3.0

    kapanis = ana_trend + dalgalanma

    hacim = np.full(
        gun_sayisi,
        1_000_000.0,
    )

    # Son iki günde yüksek hacim oluşturalım.
    hacim[-2] = 1_600_000
    hacim[-1] = 1_800_000

    return pd.DataFrame(
        {
            "Open": kapanis - 0.50,
            "High": kapanis + 2.00,
            "Low": kapanis - 2.00,
            "Close": kapanis,
            "Volume": hacim,
        },
        index=tarihler,
    )


def test_butunlesik_analiz_sonucu_uretilir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Gerçek internet verisi yerine sentetik veri kullanarak bütün
    analiz zincirini baştan sona test eder.
    """
    test_verisi = sentetik_piyasa_verisi()

    monkeypatch.setattr(
        stock_analyzer_module,
        "fiyat_verisi_getir",
        lambda **kwargs: test_verisi.copy(),
    )

    analiz_motoru = StockAnalyzer()

    sonuc = analiz_motoru.analiz_et(
        "TEST.IS"
    )

    assert sonuc.sembol == "TEST.IS"

    assert sonuc.analiz_tarihi == str(
        test_verisi.index[-1].date()
    )

    assert sonuc.kapanis > 0
    assert sonuc.hacim > 0

    assert sonuc.ema9 > 0
    assert sonuc.ema21 > 0
    assert 0 <= sonuc.rsi14 <= 100

    assert sonuc.atr14 > 0
    assert sonuc.atr_yuzde > 0
    assert sonuc.hacim_orani > 0

    assert 0 <= sonuc.sinyal.skor <= 100

    assert sonuc.sinyal.karar in {
        "Pozitif Teknik Görünüm",
        "Nötr Teknik Görünüm",
        "Negatif Teknik Görünüm",
    }

    assert sonuc.risk_plani.stop_loss < sonuc.kapanis
    assert sonuc.risk_plani.hedef_fiyat > sonuc.kapanis

    assert sonuc.destek_direnc.mevcut_fiyat == pytest.approx(
        sonuc.kapanis,
        abs=1e-10,
    )

    assert 0 < sonuc.risk_plani.risk_odul_orani

    assert sonuc.hedef_kaynagi in {
        "Yakın direnç",
        "ATR tahmini — direnç bulunamadı",
    }


def test_sembol_temizlenip_buyuk_harfe_cevrilir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_verisi = sentetik_piyasa_verisi()

    monkeypatch.setattr(
        stock_analyzer_module,
        "fiyat_verisi_getir",
        lambda **kwargs: test_verisi.copy(),
    )

    sonuc = StockAnalyzer().analiz_et(
        "  thyao.is  "
    )

    assert sonuc.sembol == "THYAO.IS"


def test_sonuc_sozluge_donusturulebilir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_verisi = sentetik_piyasa_verisi()

    monkeypatch.setattr(
        stock_analyzer_module,
        "fiyat_verisi_getir",
        lambda **kwargs: test_verisi.copy(),
    )

    sonuc = StockAnalyzer().analiz_et(
        "TEST.IS"
    )

    sonuc_sozlugu = sonuc.sozluge_donustur()

    assert sonuc_sozlugu["sembol"] == "TEST.IS"
    assert "risk_plani" in sonuc_sozlugu
    assert "sinyal" in sonuc_sozlugu

    assert isinstance(
        sonuc_sozlugu["risk_plani"],
        dict,
    )

    assert isinstance(
        sonuc_sozlugu["sinyal"],
        dict,
    )


def test_bos_sembol_kabul_edilmez() -> None:
    with pytest.raises(
        ValueError,
        match="boş olamaz",
    ):
        StockAnalyzer().analiz_et("   ")


def test_veri_kaynagi_hatasi_anlamli_hata_olur(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def hata_uret(**kwargs):
        raise MarketDataError(
            "Test veri kaynağı hatası."
        )

    monkeypatch.setattr(
        stock_analyzer_module,
        "fiyat_verisi_getir",
        hata_uret,
    )

    with pytest.raises(
        StockAnalyzerError,
        match="analiz edilemedi",
    ):
        StockAnalyzer().analiz_et(
            "TEST.IS"
        )