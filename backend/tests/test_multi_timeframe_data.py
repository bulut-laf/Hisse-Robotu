from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from backend.app.data.multi_timeframe_data import (
    GUNLUK,
    HAFTALIK,
    SAATLIK,
    MultiTimeframeDataError,
    TimeframeConfig,
    bist_sembolunu_hazirla,
    coklu_zaman_dilimi_verisi_getir,
)


ISTANBUL = ZoneInfo("Europe/Istanbul")


def fiyat_verisi(
    baslangic: str,
    bar: int,
    freq: str,
    tz: str | None = None,
) -> pd.DataFrame:
    indeks = pd.date_range(
        baslangic,
        periods=bar,
        freq=freq,
        tz=tz,
    )
    kapanislar = [100.0 + konum for konum in range(bar)]

    return pd.DataFrame(
        {
            "Open": [fiyat - 0.5 for fiyat in kapanislar],
            "High": [fiyat + 1.0 for fiyat in kapanislar],
            "Low": [fiyat - 1.0 for fiyat in kapanislar],
            "Close": kapanislar,
            "Volume": [1_000_000.0 + konum for konum in range(bar)],
        },
        index=indeks,
    )


def uc_zaman_dilimi_ayari(
    minimum_bar: int = 2,
    maksimum_bar: int = 10,
) -> tuple[TimeframeConfig, ...]:
    return (
        TimeframeConfig(SAATLIK, "1h", "5d", maksimum_bar, minimum_bar),
        TimeframeConfig(GUNLUK, "1d", "1mo", maksimum_bar, minimum_bar),
        TimeframeConfig(HAFTALIK, "1wk", "6mo", maksimum_bar, minimum_bar),
    )


def test_bist_sembolune_is_eki_eklenir() -> None:
    assert bist_sembolunu_hazirla(" thyao ") == "THYAO.IS"


def test_hazir_bist_sembolu_degismez() -> None:
    assert bist_sembolunu_hazirla("THYAO.IS") == "THYAO.IS"


def test_bos_sembol_reddedilir() -> None:
    with pytest.raises(ValueError, match="boş olamaz"):
        bist_sembolunu_hazirla("   ")


def test_zaman_dilimi_ayari_gecersiz_araligi_reddeder() -> None:
    with pytest.raises(ValueError, match="Desteklenmeyen"):
        TimeframeConfig("Dört Saat", "4h", "60d", 100, 20)


def test_ayni_adli_zaman_dilimleri_reddedilir() -> None:
    ayarlar = (
        TimeframeConfig("Günlük", "1d", "1y", 100, 2),
        TimeframeConfig("Günlük", "1wk", "5y", 100, 2),
    )

    with pytest.raises(ValueError, match="adları benzersiz"):
        coklu_zaman_dilimi_verisi_getir(
            "THYAO",
            zaman_dilimleri=ayarlar,
            veri_indirici=lambda **kwargs: fiyat_verisi(
                "2025-01-01", 10, "D"
            ),
        )


def test_uc_zaman_dilimi_ayni_bist_semboluyle_indirilir() -> None:
    cagrilar: list[dict[str, object]] = []

    def indirici(**kwargs: object) -> pd.DataFrame:
        cagrilar.append(kwargs)
        interval = str(kwargs["interval"])
        frekans = {"1h": "h", "1d": "D", "1wk": "7D"}[interval]
        return fiyat_verisi("2025-01-01", 5, frekans)

    paket = coklu_zaman_dilimi_verisi_getir(
        "THYAO",
        zaman_dilimleri=uc_zaman_dilimi_ayari(),
        veri_indirici=indirici,
        simdi=datetime(2026, 1, 1, 20, 0, tzinfo=ISTANBUL),
    )

    assert paket.sembol == "THYAO.IS"
    assert [cagri["tickers"] for cagri in cagrilar] == [
        "THYAO.IS",
        "THYAO.IS",
        "THYAO.IS",
    ]
    assert [cagri["interval"] for cagri in cagrilar] == [
        "1h",
        "1d",
        "1wk",
    ]


def test_saatlik_tamamlanmamis_son_bar_cikarilir() -> None:
    ayar = (TimeframeConfig(SAATLIK, "1h", "5d", 10, 2),)
    veri = fiyat_verisi("2026-01-05 10:00", 3, "h")

    paket = coklu_zaman_dilimi_verisi_getir(
        "THYAO",
        zaman_dilimleri=ayar,
        veri_indirici=lambda **kwargs: veri,
        simdi=datetime(2026, 1, 5, 12, 30, tzinfo=ISTANBUL),
    )

    sonuc = paket.getir(SAATLIK)
    assert sonuc.bar_sayisi == 2
    assert sonuc.tamamlanmamis_bar_cikarildi is True
    assert sonuc.son_zaman == pd.Timestamp("2026-01-05 11:00")


def test_tamamlanmis_saatlik_bar_korunur() -> None:
    ayar = (TimeframeConfig(SAATLIK, "1h", "5d", 10, 2),)
    veri = fiyat_verisi("2026-01-05 10:00", 3, "h")

    paket = coklu_zaman_dilimi_verisi_getir(
        "THYAO",
        zaman_dilimleri=ayar,
        veri_indirici=lambda **kwargs: veri,
        simdi=datetime(2026, 1, 5, 13, 5, tzinfo=ISTANBUL),
    )

    sonuc = paket.getir(SAATLIK)
    assert sonuc.bar_sayisi == 3
    assert sonuc.tamamlanmamis_bar_cikarildi is False


def test_gunluk_mum_seans_kapanmadan_once_cikarilir() -> None:
    ayar = (TimeframeConfig(GUNLUK, "1d", "1mo", 10, 2),)
    veri = fiyat_verisi("2026-01-03", 3, "D")

    paket = coklu_zaman_dilimi_verisi_getir(
        "THYAO",
        zaman_dilimleri=ayar,
        veri_indirici=lambda **kwargs: veri,
        simdi=datetime(2026, 1, 5, 17, 0, tzinfo=ISTANBUL),
    )

    sonuc = paket.getir(GUNLUK)
    assert sonuc.bar_sayisi == 2
    assert sonuc.son_zaman == pd.Timestamp("2026-01-04")


def test_haftalik_mum_cuma_kapanmadan_once_cikarilir() -> None:
    ayar = (TimeframeConfig(HAFTALIK, "1wk", "6mo", 10, 2),)
    veri = fiyat_verisi("2025-12-22", 3, "7D")

    paket = coklu_zaman_dilimi_verisi_getir(
        "THYAO",
        zaman_dilimleri=ayar,
        veri_indirici=lambda **kwargs: veri,
        simdi=datetime(2026, 1, 7, 12, 0, tzinfo=ISTANBUL),
    )

    sonuc = paket.getir(HAFTALIK)
    assert sonuc.bar_sayisi == 2
    assert sonuc.son_zaman == pd.Timestamp("2025-12-29")


def test_veri_siralanir_ve_yinelenen_zaman_silinir() -> None:
    ayar = (TimeframeConfig(GUNLUK, "1d", "1mo", 10, 2),)
    veri = fiyat_verisi("2025-01-01", 3, "D")
    yinelenen = pd.concat(
        [veri.iloc[[2]], veri.iloc[[0]], veri.iloc[[1]], veri.iloc[[2]]]
    )
    yinelenen.iloc[-1, yinelenen.columns.get_loc("Close")] = 999.0

    paket = coklu_zaman_dilimi_verisi_getir(
        "THYAO",
        zaman_dilimleri=ayar,
        veri_indirici=lambda **kwargs: yinelenen,
        simdi=datetime(2026, 1, 1, 20, 0, tzinfo=ISTANBUL),
    )

    sonuc = paket.getir(GUNLUK).veri
    assert sonuc.index.is_monotonic_increasing
    assert sonuc.index.is_unique
    assert sonuc.iloc[-1]["Close"] == pytest.approx(999.0)


def test_maksimum_bar_siniri_uygulanir() -> None:
    ayar = (TimeframeConfig(GUNLUK, "1d", "1mo", 3, 2),)
    veri = fiyat_verisi("2025-01-01", 8, "D")

    paket = coklu_zaman_dilimi_verisi_getir(
        "THYAO",
        zaman_dilimleri=ayar,
        veri_indirici=lambda **kwargs: veri,
        simdi=datetime(2026, 1, 1, 20, 0, tzinfo=ISTANBUL),
    )

    sonuc = paket.getir(GUNLUK)
    assert sonuc.bar_sayisi == 3
    assert sonuc.ilk_zaman == pd.Timestamp("2025-01-06")


def test_yetersiz_bar_zaman_dilimi_adiyla_hata_verir() -> None:
    ayar = (TimeframeConfig(HAFTALIK, "1wk", "6mo", 10, 5),)
    veri = fiyat_verisi("2025-01-01", 3, "7D")

    with pytest.raises(
        MultiTimeframeDataError,
        match="Haftalık verisinde yalnızca 3",
    ):
        coklu_zaman_dilimi_verisi_getir(
            "THYAO",
            zaman_dilimleri=ayar,
            veri_indirici=lambda **kwargs: veri,
            simdi=datetime(2026, 1, 1, 20, 0, tzinfo=ISTANBUL),
        )


def test_saat_dilimli_indeks_istanbul_saatine_cevrilir() -> None:
    ayar = (TimeframeConfig(SAATLIK, "1h", "5d", 10, 2),)
    veri = fiyat_verisi("2025-01-01 08:00", 3, "h", tz="UTC")

    paket = coklu_zaman_dilimi_verisi_getir(
        "THYAO",
        zaman_dilimleri=ayar,
        veri_indirici=lambda **kwargs: veri,
        simdi=datetime(2026, 1, 1, 20, 0, tzinfo=ISTANBUL),
    )

    sonuc = paket.getir(SAATLIK).veri
    assert sonuc.index.tz is None
    assert sonuc.index[0] == pd.Timestamp("2025-01-01 11:00")


def test_ayni_veri_ayni_paket_kimligini_uretir() -> None:
    ayarlar = uc_zaman_dilimi_ayari()

    def indirici(**kwargs: object) -> pd.DataFrame:
        interval = str(kwargs["interval"])
        frekans = {"1h": "h", "1d": "D", "1wk": "7D"}[interval]
        return fiyat_verisi("2025-01-01", 5, frekans)

    birinci = coklu_zaman_dilimi_verisi_getir(
        "THYAO",
        zaman_dilimleri=ayarlar,
        veri_indirici=indirici,
        simdi=datetime(2026, 1, 1, 20, 0, tzinfo=ISTANBUL),
    )
    ikinci = coklu_zaman_dilimi_verisi_getir(
        "THYAO",
        zaman_dilimleri=ayarlar,
        veri_indirici=indirici,
        simdi=datetime(2026, 1, 1, 20, 0, tzinfo=ISTANBUL),
    )

    assert birinci.veri_kimligi == ikinci.veri_kimligi
    assert len(birinci.veri_kimligi) == 12


def test_bir_zaman_dilimindeki_fiyat_degisikligi_paket_kimligini_degistirir() -> None:
    ayarlar = uc_zaman_dilimi_ayari()
    degistir = False

    def indirici(**kwargs: object) -> pd.DataFrame:
        interval = str(kwargs["interval"])
        frekans = {"1h": "h", "1d": "D", "1wk": "7D"}[interval]
        veri = fiyat_verisi("2025-01-01", 5, frekans)
        if degistir and interval == "1d":
            veri.iloc[-1, veri.columns.get_loc("Close")] += 1.0
        return veri

    birinci = coklu_zaman_dilimi_verisi_getir(
        "THYAO",
        zaman_dilimleri=ayarlar,
        veri_indirici=indirici,
        simdi=datetime(2026, 1, 1, 20, 0, tzinfo=ISTANBUL),
    )
    degistir = True
    ikinci = coklu_zaman_dilimi_verisi_getir(
        "THYAO",
        zaman_dilimleri=ayarlar,
        veri_indirici=indirici,
        simdi=datetime(2026, 1, 1, 20, 0, tzinfo=ISTANBUL),
    )

    assert birinci.veri_kimligi != ikinci.veri_kimligi


def test_terminal_calistiricisi_dogrudan_dosya_olarak_acilir() -> None:
    proje_koku = Path(__file__).resolve().parents[2]
    calistirici = proje_koku / "backend" / "run_multi_timeframe_data.py"

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
    assert "saatlik, günlük ve haftalık" in sonuc.stdout
    assert "ModuleNotFoundError" not in sonuc.stderr
