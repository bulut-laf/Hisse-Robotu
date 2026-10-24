from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from backend.app.analysis.multi_timeframe_analysis import (
    GUCLU_NEGATIF_UYUM,
    GUCLU_POZITIF_UYUM,
    NEGATIF,
    NOTR,
    POZITIF,
    POZITIF_SAATLIK_TEYIT_BEKLENIYOR,
    TEPKI_YUKSELISI_RISKI,
    TREND_GUNLUK_CELISKILI,
    MultiTimeframeAnalysisError,
    coklu_zaman_dilimi_teknik_analizi_yap,
)
from backend.app.data.multi_timeframe_data import (
    GUNLUK,
    HAFTALIK,
    SAATLIK,
    MultiTimeframeDataBundle,
    TimeframeSnapshot,
)


def fiyat_verisi(
    yon: str,
    bar: int = 120,
    baslangic: str = "2025-01-01",
    frekans: str = "D",
) -> pd.DataFrame:
    indeks = pd.date_range(baslangic, periods=bar, freq=frekans)
    x = np.arange(bar, dtype=float)

    if yon == "pozitif":
        kapanis = 100.0 + x * 0.05 + np.sin(x / 2.3) * 1.80
    elif yon == "negatif":
        kapanis = 200.0 - x * 0.60 + np.sin(x / 4.0) * 0.35
    elif yon == "notr":
        kapanis = 100.0 + np.sin(x / 3.0) * 1.20
    else:
        raise ValueError(f"Bilinmeyen yön: {yon}")

    return pd.DataFrame(
        {
            "Open": kapanis - 0.30,
            "High": kapanis + 1.00,
            "Low": kapanis - 1.00,
            "Close": kapanis,
            "Volume": 1_000_000.0 + x * 1_000.0,
        },
        index=indeks,
    )


def snapshot(ad: str, interval: str, yon: str) -> TimeframeSnapshot:
    frekans = {SAATLIK: "h", GUNLUK: "D", HAFTALIK: "7D"}[ad]
    return TimeframeSnapshot(
        ad=ad,
        interval=interval,
        period="test",
        veri=fiyat_verisi(yon, frekans=frekans),
        tamamlanmamis_bar_cikarildi=False,
        veri_kimligi=f"{ad}-{yon}",
    )


def paket(
    haftalik: str = "pozitif",
    gunluk: str = "pozitif",
    saatlik: str = "pozitif",
    veri_kimligi: str = "paket-1",
) -> MultiTimeframeDataBundle:
    return MultiTimeframeDataBundle(
        sembol="THYAO.IS",
        zaman_dilimleri=(
            snapshot(SAATLIK, "1h", saatlik),
            snapshot(GUNLUK, "1d", gunluk),
            snapshot(HAFTALIK, "1wk", haftalik),
        ),
        veri_kimligi=veri_kimligi,
    )


def test_uc_pozitif_zaman_dilimi_guclu_pozitif_uyum_uretir() -> None:
    sonuc = coklu_zaman_dilimi_teknik_analizi_yap(paket())

    assert sonuc.haftalik.yon == POZITIF
    assert sonuc.gunluk.yon == POZITIF
    assert sonuc.saatlik.yon == POZITIF
    assert sonuc.teyit_durumu == GUCLU_POZITIF_UYUM
    assert sonuc.uyum_skoru >= 70


def test_uc_negatif_zaman_dilimi_guclu_negatif_uyum_uretir() -> None:
    sonuc = coklu_zaman_dilimi_teknik_analizi_yap(
        paket("negatif", "negatif", "negatif")
    )

    assert sonuc.haftalik.yon == NEGATIF
    assert sonuc.gunluk.yon == NEGATIF
    assert sonuc.saatlik.yon == NEGATIF
    assert sonuc.teyit_durumu == GUCLU_NEGATIF_UYUM
    assert sonuc.uyum_skoru < 40


def test_haftalik_ve_gunluk_pozitif_saatlik_negatifse_teyit_beklenir() -> None:
    sonuc = coklu_zaman_dilimi_teknik_analizi_yap(
        paket("pozitif", "pozitif", "negatif")
    )

    assert sonuc.teyit_durumu == POZITIF_SAATLIK_TEYIT_BEKLENIYOR
    assert "Saatlik zamanlama negatif." in sonuc.riskler


def test_pozitif_haftalik_negatif_gunluk_celiski_olarak_isaretlenir() -> None:
    sonuc = coklu_zaman_dilimi_teknik_analizi_yap(
        paket("pozitif", "negatif", "pozitif")
    )

    assert sonuc.teyit_durumu == TREND_GUNLUK_CELISKILI
    assert "Zaman dilimleri arasında yön uyuşmazlığı var." in sonuc.riskler


def test_negatif_haftalik_pozitif_gunluk_tepkisel_risk_olarak_isaretlenir() -> None:
    sonuc = coklu_zaman_dilimi_teknik_analizi_yap(
        paket("negatif", "pozitif", "pozitif")
    )

    assert sonuc.teyit_durumu == TEPKI_YUKSELISI_RISKI


def test_zaman_dilimleri_birbirinden_bagimsiz_hesaplanir() -> None:
    sonuc = coklu_zaman_dilimi_teknik_analizi_yap(
        paket("pozitif", "negatif", "pozitif")
    )

    assert sonuc.haftalik.skor != sonuc.gunluk.skor
    assert sonuc.haftalik.yon == POZITIF
    assert sonuc.gunluk.yon == NEGATIF
    assert sonuc.saatlik.yon == POZITIF


def test_uyum_skoru_agirlikli_ortalama_olarak_hesaplanir() -> None:
    sonuc = coklu_zaman_dilimi_teknik_analizi_yap(
        paket("pozitif", "negatif", "pozitif")
    )
    beklenen = round(
        sonuc.haftalik.skor * 0.45
        + sonuc.gunluk.skor * 0.35
        + sonuc.saatlik.skor * 0.20
    )

    assert sonuc.uyum_skoru == beklenen


def test_sonuc_teknik_degerleri_tasir() -> None:
    sonuc = coklu_zaman_dilimi_teknik_analizi_yap(paket())

    assert sonuc.gunluk.kapanis > 0
    assert sonuc.gunluk.ema9 > 0
    assert sonuc.gunluk.ema21 > 0
    assert 0 <= sonuc.gunluk.rsi14 <= 100
    assert isinstance(sonuc.gunluk.son_zaman, pd.Timestamp)


def test_getir_zaman_dilimi_adini_buyuk_kucuk_harfsiz_bulur() -> None:
    sonuc = coklu_zaman_dilimi_teknik_analizi_yap(paket())

    assert sonuc.getir("gÜnLÜk") == sonuc.gunluk


def test_getir_bilinmeyen_zaman_diliminde_key_error_verir() -> None:
    sonuc = coklu_zaman_dilimi_teknik_analizi_yap(paket())

    with pytest.raises(KeyError, match="bulunamadı"):
        sonuc.getir("Aylık")


def test_eksik_zaman_dilimi_anlamli_hata_verir() -> None:
    eksik = MultiTimeframeDataBundle(
        sembol="THYAO.IS",
        zaman_dilimleri=(
            snapshot(GUNLUK, "1d", "pozitif"),
            snapshot(HAFTALIK, "1wk", "pozitif"),
        ),
        veri_kimligi="eksik",
    )

    with pytest.raises(
        MultiTimeframeAnalysisError,
        match="eksik zaman dilimleri: Saatlik",
    ):
        coklu_zaman_dilimi_teknik_analizi_yap(eksik)


def test_yinelenen_zaman_dilimi_reddedilir() -> None:
    yinelenen = MultiTimeframeDataBundle(
        sembol="THYAO.IS",
        zaman_dilimleri=(
            snapshot(SAATLIK, "1h", "pozitif"),
            snapshot(GUNLUK, "1d", "pozitif"),
            snapshot(GUNLUK, "1d", "negatif"),
            snapshot(HAFTALIK, "1wk", "pozitif"),
        ),
        veri_kimligi="yinelenen",
    )

    with pytest.raises(
        MultiTimeframeAnalysisError,
        match="Yinelenen zaman dilimi",
    ):
        coklu_zaman_dilimi_teknik_analizi_yap(yinelenen)


def test_yetersiz_gosterge_gecmisi_anlamli_hata_verir() -> None:
    kisa = snapshot(GUNLUK, "1d", "pozitif")
    kisa = TimeframeSnapshot(
        ad=kisa.ad,
        interval=kisa.interval,
        period=kisa.period,
        veri=kisa.veri.head(20),
        tamamlanmamis_bar_cikarildi=False,
        veri_kimligi="kisa",
    )
    kisa_paket = MultiTimeframeDataBundle(
        sembol="THYAO.IS",
        zaman_dilimleri=(
            snapshot(SAATLIK, "1h", "pozitif"),
            kisa,
            snapshot(HAFTALIK, "1wk", "pozitif"),
        ),
        veri_kimligi="kisa-paket",
    )

    with pytest.raises(
        MultiTimeframeAnalysisError,
        match="Günlük teknik analizi için",
    ):
        coklu_zaman_dilimi_teknik_analizi_yap(kisa_paket)


def test_ayni_veri_ayni_analiz_kimligini_uretir() -> None:
    birinci = coklu_zaman_dilimi_teknik_analizi_yap(paket())
    ikinci = coklu_zaman_dilimi_teknik_analizi_yap(paket())

    assert birinci.analiz_kimligi == ikinci.analiz_kimligi
    assert len(birinci.analiz_kimligi) == 12


def test_veri_kimligi_degisirse_analiz_kimligi_degisir() -> None:
    birinci = coklu_zaman_dilimi_teknik_analizi_yap(
        paket(veri_kimligi="paket-a")
    )
    ikinci = coklu_zaman_dilimi_teknik_analizi_yap(
        paket(veri_kimligi="paket-b")
    )

    assert birinci.analiz_kimligi != ikinci.analiz_kimligi


def test_terminal_calistiricisi_dogrudan_dosya_olarak_acilir() -> None:
    proje_koku = Path(__file__).resolve().parents[2]
    calistirici = proje_koku / "backend" / "run_multi_timeframe_analysis.py"

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
    assert "haftalık trend, günlük yön teyidi" in sonuc.stdout
    assert "ModuleNotFoundError" not in sonuc.stderr
