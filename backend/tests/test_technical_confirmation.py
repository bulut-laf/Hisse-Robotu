from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from backend.app.analysis.technical_confirmation import (
    DEATH_CROSS,
    EMA_NEGATIF_KESISIM,
    EMA_POZITIF_KESISIM,
    ERKEN_ASAGI_UYARI,
    ERKEN_YUKARI_UYARI,
    GOLDEN_CROSS,
    TEYITLI_ASAGI_KIRILIM,
    TEYITLI_YUKARI_KIRILIM,
    TechnicalConfirmationError,
    teknik_teyit_analizi_yap,
    zaman_dilimi_teyidini_hesapla,
)
from backend.app.data.multi_timeframe_data import (
    GUNLUK,
    HAFTALIK,
    SAATLIK,
    MultiTimeframeDataBundle,
    TimeframeSnapshot,
)


def _temel_veri(
    bar: int = 260,
    frekans: str = "D",
    kapanis: float = 100.0,
) -> pd.DataFrame:
    indeks = pd.date_range("2025-01-01", periods=bar, freq=frekans)
    fiyatlar = np.full(bar, kapanis, dtype=float)
    return pd.DataFrame(
        {
            "Open": fiyatlar - 0.20,
            "High": fiyatlar + 1.00,
            "Low": fiyatlar - 1.00,
            "Close": fiyatlar,
            "Volume": np.full(bar, 1_000_000.0),
        },
        index=indeks,
    )


def _yukari_kirilim_verisi(
    kapanis_teyidi: bool = True,
    yuksek_hacim: bool = True,
) -> pd.DataFrame:
    veri = _temel_veri()
    x = np.arange(len(veri), dtype=float)
    kapanislar = 100.0 + x * 0.02 + np.sin(x / 8.0) * 0.80
    veri["Close"] = kapanislar
    veri["Open"] = kapanislar - 0.20
    veri["High"] = kapanislar + 0.80
    veri["Low"] = kapanislar - 0.80

    veri.iloc[210, veri.columns.get_loc("High")] = 115.0
    veri.iloc[240, veri.columns.get_loc("High")] = 111.0

    veri.iloc[258, veri.columns.get_loc("Open")] = 107.80
    veri.iloc[258, veri.columns.get_loc("High")] = 108.30
    veri.iloc[258, veri.columns.get_loc("Low")] = 107.50
    veri.iloc[258, veri.columns.get_loc("Close")] = 108.00

    veri.iloc[259, veri.columns.get_loc("Open")] = 108.00
    veri.iloc[259, veri.columns.get_loc("Low")] = 107.80
    if kapanis_teyidi:
        veri.iloc[259, veri.columns.get_loc("High")] = 109.80
        veri.iloc[259, veri.columns.get_loc("Close")] = 109.20
    else:
        veri.iloc[259, veri.columns.get_loc("High")] = 109.20
        veri.iloc[259, veri.columns.get_loc("Close")] = 108.20

    if yuksek_hacim:
        veri.iloc[259, veri.columns.get_loc("Volume")] = 2_000_000.0
    return veri


def _asagi_kirilim_verisi(
    kapanis_teyidi: bool = True,
) -> pd.DataFrame:
    veri = _temel_veri()
    x = np.arange(len(veri), dtype=float)
    kapanislar = 105.0 + x * 0.01 + np.sin(x / 9.0) * 0.70
    veri["Close"] = kapanislar
    veri["Open"] = kapanislar + 0.20
    veri["High"] = kapanislar + 0.80
    veri["Low"] = kapanislar - 0.80

    veri.iloc[210, veri.columns.get_loc("Low")] = 92.0
    veri.iloc[240, veri.columns.get_loc("Low")] = 96.0

    veri.iloc[258, veri.columns.get_loc("Open")] = 99.20
    veri.iloc[258, veri.columns.get_loc("High")] = 99.50
    veri.iloc[258, veri.columns.get_loc("Low")] = 98.70
    veri.iloc[258, veri.columns.get_loc("Close")] = 99.00

    veri.iloc[259, veri.columns.get_loc("Open")] = 99.10
    veri.iloc[259, veri.columns.get_loc("High")] = 99.40
    if kapanis_teyidi:
        veri.iloc[259, veri.columns.get_loc("Low")] = 97.60
        veri.iloc[259, veri.columns.get_loc("Close")] = 98.00
    else:
        veri.iloc[259, veri.columns.get_loc("Low")] = 98.00
        veri.iloc[259, veri.columns.get_loc("Close")] = 99.00

    veri.iloc[259, veri.columns.get_loc("Volume")] = 1_800_000.0
    return veri


def _snapshot(
    ad: str,
    veri: pd.DataFrame,
    veri_kimligi: str | None = None,
) -> TimeframeSnapshot:
    interval = {SAATLIK: "1h", GUNLUK: "1d", HAFTALIK: "1wk"}[ad]
    return TimeframeSnapshot(
        ad=ad,
        interval=interval,
        period="test",
        veri=veri,
        tamamlanmamis_bar_cikarildi=False,
        veri_kimligi=veri_kimligi or f"{ad}-veri",
    )


def _kapanis_verisi(kapanislar: np.ndarray) -> pd.DataFrame:
    veri = _temel_veri(bar=len(kapanislar))
    veri["Open"] = kapanislar - 0.20
    veri["High"] = kapanislar + 1.00
    veri["Low"] = kapanislar - 1.00
    veri["Close"] = kapanislar
    return veri


def _paket(veri_kimligi: str = "paket-1") -> MultiTimeframeDataBundle:
    return MultiTimeframeDataBundle(
        sembol="THYAO.IS",
        zaman_dilimleri=(
            _snapshot(SAATLIK, _yukari_kirilim_verisi()),
            _snapshot(GUNLUK, _yukari_kirilim_verisi()),
            _snapshot(HAFTALIK, _yukari_kirilim_verisi()),
        ),
        veri_kimligi=veri_kimligi,
    )


def test_teyitli_yukari_kirilim_kapanisla_ayrilir() -> None:
    sonuc = zaman_dilimi_teyidini_hesapla(
        _snapshot(GUNLUK, _yukari_kirilim_verisi())
    )

    assert sonuc.kirilim.durum == TEYITLI_YUKARI_KIRILIM
    assert sonuc.kirilim.kapanis_teyidi is True
    assert sonuc.kirilim.erken_uyari is False


def test_erken_yukari_uyari_kapanis_teyidi_sayilmaz() -> None:
    sonuc = zaman_dilimi_teyidini_hesapla(
        _snapshot(GUNLUK, _yukari_kirilim_verisi(False))
    )

    assert sonuc.kirilim.durum == ERKEN_YUKARI_UYARI
    assert sonuc.kirilim.kapanis_teyidi is False
    assert sonuc.kirilim.erken_uyari is True


def test_teyitli_asagi_kirilim_kapanisla_ayrilir() -> None:
    sonuc = zaman_dilimi_teyidini_hesapla(
        _snapshot(GUNLUK, _asagi_kirilim_verisi())
    )

    assert sonuc.kirilim.durum == TEYITLI_ASAGI_KIRILIM
    assert sonuc.kirilim.kapanis_teyidi is True


def test_erken_asagi_uyari_kapanis_teyidi_sayilmaz() -> None:
    sonuc = zaman_dilimi_teyidini_hesapla(
        _snapshot(GUNLUK, _asagi_kirilim_verisi(False))
    )

    assert sonuc.kirilim.durum == ERKEN_ASAGI_UYARI
    assert sonuc.kirilim.erken_uyari is True


def test_yukari_kirilim_yuksek_hacimle_teyit_edilir() -> None:
    sonuc = zaman_dilimi_teyidini_hesapla(
        _snapshot(GUNLUK, _yukari_kirilim_verisi(yuksek_hacim=True))
    )

    assert sonuc.kirilim.hacim_orani == pytest.approx(2.0)
    assert sonuc.kirilim.hacim_teyidi is True


def test_kirilim_normal_hacimde_hacim_teyidi_almaz() -> None:
    sonuc = zaman_dilimi_teyidini_hesapla(
        _snapshot(GUNLUK, _yukari_kirilim_verisi(yuksek_hacim=False))
    )

    assert sonuc.kirilim.hacim_orani == pytest.approx(1.0)
    assert sonuc.kirilim.hacim_teyidi is False


def test_ema9_21_pozitif_kesisim_bulunur() -> None:
    kapanislar = np.r_[np.full(230, 100.0), np.full(29, 90.0), 150.0]
    sonuc = zaman_dilimi_teyidini_hesapla(
        _snapshot(GUNLUK, _kapanis_verisi(kapanislar))
    )

    assert sonuc.ortalamalar.ema9_21_durumu == EMA_POZITIF_KESISIM


def test_ema21_55_negatif_kesisim_bulunur() -> None:
    kapanislar = np.r_[np.full(230, 100.0), np.full(29, 110.0), 50.0]
    sonuc = zaman_dilimi_teyidini_hesapla(
        _snapshot(GUNLUK, _kapanis_verisi(kapanislar))
    )

    assert sonuc.ortalamalar.ema21_55_durumu == EMA_NEGATIF_KESISIM


def test_golden_cross_bulunur() -> None:
    kapanislar = np.r_[np.full(200, 1000.0), np.full(49, 990.0), 1500.0]
    sonuc = zaman_dilimi_teyidini_hesapla(
        _snapshot(GUNLUK, _kapanis_verisi(kapanislar))
    )

    assert sonuc.ortalamalar.golden_cross is True
    assert sonuc.ortalamalar.uzun_vade_durumu == GOLDEN_CROSS


def test_death_cross_bulunur() -> None:
    kapanislar = np.r_[np.full(200, 1000.0), np.full(49, 1010.0), 500.0]
    sonuc = zaman_dilimi_teyidini_hesapla(
        _snapshot(GUNLUK, _kapanis_verisi(kapanislar))
    )

    assert sonuc.ortalamalar.death_cross is True
    assert sonuc.ortalamalar.uzun_vade_durumu == DEATH_CROSS


def test_momentum_rsi_macd_degerlerini_tasir() -> None:
    sonuc = zaman_dilimi_teyidini_hesapla(
        _snapshot(GUNLUK, _yukari_kirilim_verisi())
    )

    assert 0 <= sonuc.momentum.rsi14 <= 100
    assert isinstance(sonuc.momentum.macd, float)
    assert isinstance(sonuc.momentum.macd_histogram, float)


def test_destek_direnc_sonuclari_tasinir() -> None:
    sonuc = zaman_dilimi_teyidini_hesapla(
        _snapshot(GUNLUK, _yukari_kirilim_verisi())
    )

    assert sonuc.destek is not None
    assert sonuc.direnc is not None
    assert sonuc.destek < sonuc.kapanis < sonuc.direnc


def test_uc_zaman_dilimi_bagimsiz_hesaplanir() -> None:
    paket = MultiTimeframeDataBundle(
        sembol="THYAO.IS",
        zaman_dilimleri=(
            _snapshot(SAATLIK, _yukari_kirilim_verisi()),
            _snapshot(GUNLUK, _asagi_kirilim_verisi()),
            _snapshot(HAFTALIK, _yukari_kirilim_verisi(False)),
        ),
        veri_kimligi="karma",
    )
    sonuc = teknik_teyit_analizi_yap(paket)

    assert sonuc.saatlik.kirilim.durum == TEYITLI_YUKARI_KIRILIM
    assert sonuc.gunluk.kirilim.durum == TEYITLI_ASAGI_KIRILIM
    assert sonuc.haftalik.kirilim.durum == ERKEN_YUKARI_UYARI
    assert sonuc.getir("gÜnLÜk") == sonuc.gunluk


def test_eksik_zaman_dilimi_hata_verir() -> None:
    eksik = MultiTimeframeDataBundle(
        sembol="THYAO.IS",
        zaman_dilimleri=(
            _snapshot(GUNLUK, _yukari_kirilim_verisi()),
            _snapshot(HAFTALIK, _yukari_kirilim_verisi()),
        ),
        veri_kimligi="eksik",
    )

    with pytest.raises(
        TechnicalConfirmationError,
        match="eksik zaman dilimleri: Saatlik",
    ):
        teknik_teyit_analizi_yap(eksik)


def test_analiz_kimligi_ayni_veride_sabittir() -> None:
    birinci = teknik_teyit_analizi_yap(_paket())
    ikinci = teknik_teyit_analizi_yap(_paket())

    assert birinci.analiz_kimligi == ikinci.analiz_kimligi
    assert len(birinci.analiz_kimligi) == 12


def test_veri_kimligi_degisiminde_analiz_kimligi_degisir() -> None:
    birinci = teknik_teyit_analizi_yap(_paket("paket-a"))
    ikinci = teknik_teyit_analizi_yap(_paket("paket-b"))

    assert birinci.analiz_kimligi != ikinci.analiz_kimligi


def test_terminal_calistiricisi_dogrudan_dosya_olarak_acilir() -> None:
    proje_koku = Path(__file__).resolve().parents[2]
    calistirici = proje_koku / "backend" / "run_technical_confirmation.py"

    sonuc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(calistirici),
            "--help",
        ],
        cwd=proje_koku,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert sonuc.returncode == 0, sonuc.stderr
    assert "trend çizgisi kırılımı, hacim teyidi" in sonuc.stdout
    assert "ModuleNotFoundError" not in sonuc.stderr
