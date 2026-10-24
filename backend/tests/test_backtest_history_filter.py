from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

import pytest

from backend.app.history.backtest_history import (
    PORTFOY_ANALIZI,
    TEK_HISSE_ANALIZI,
    BacktestHistoryRecord,
)
from backend.app.history.backtest_history_filter import (
    BacktestHistoryFilter,
    gecmis_kayitlarini_filtrele,
    kayit_sembolleri,
    kayit_tarih_araligi,
)


DASHBOARD_DOSYASI = Path(__file__).resolve().parents[1] / "dashboard.py"


def kayit(
    kimlik: str,
    *,
    zaman: str = "2026-07-25T20:00:00+03:00",
    baslik: str = "THYAO.IS · Tek Hisse Backtest",
    semboller: tuple[str, ...] = ("THYAO.IS",),
    analiz_turu: str = TEK_HISSE_ANALIZI,
    analiz_kimligi: str | None = "analiz-1",
    veri_kimligi: str = "veri-1",
    ayar_kimligi: str = "ayar-1",
) -> BacktestHistoryRecord:
    return BacktestHistoryRecord(
        kayit_kimligi=kimlik,
        analiz_turu=analiz_turu,
        kaydedilme_zamani=zaman,
        baslik=baslik,
        semboller=semboller,
        donem="2021-01-01 — 2026-01-01",
        tamamlanan_islem_sayisi=100,
        atlanan_islem_sayisi=20,
        bitis_sermayesi=150_000.0,
        toplam_getiri_yuzde=50.0,
        maksimum_dusus_yuzde=20.0,
        guncel_dusus_yuzde=5.0,
        kar_faktoru=1.5,
        kazanma_yuzde=55.0,
        ortalama_sermaye_kullanim_yuzde=None,
        maksimum_pozisyon=None,
        analiz_kimligi=analiz_kimligi,
        veri_kimligi=veri_kimligi,
        ayar_kimligi=ayar_kimligi,
        dosyalar=(),
    )


def test_bos_filtre_kayit_sirasini_korur() -> None:
    kayitlar = (kayit("c"), kayit("b"), kayit("a"))

    sonuc = gecmis_kayitlarini_filtrele(
        kayitlar,
        BacktestHistoryFilter(),
    )

    assert sonuc == kayitlar


def test_arama_baslikta_buyuk_kucuk_harf_duyarsizdir() -> None:
    kayitlar = (
        kayit("a", baslik="THYAO.IS · Tek Hisse Backtest"),
        kayit("b", baslik="ASELS.IS · Tek Hisse Backtest"),
    )

    sonuc = gecmis_kayitlarini_filtrele(
        kayitlar,
        BacktestHistoryFilter(arama="asels"),
    )

    assert tuple(k.kayit_kimligi for k in sonuc) == ("b",)


def test_arama_sembol_ve_kimliklerde_calisir() -> None:
    kayitlar = (
        kayit("a", semboller=("THYAO.IS",), veri_kimligi="veri-ozel"),
        kayit(
            "b",
            baslik="TUPRS.IS · Tek Hisse Backtest",
            semboller=("TUPRS.IS",),
            ayar_kimligi="ayar-ozel",
        ),
    )

    assert gecmis_kayitlarini_filtrele(
        kayitlar,
        BacktestHistoryFilter(arama="THYAO"),
    ) == (kayitlar[0],)
    assert gecmis_kayitlarini_filtrele(
        kayitlar,
        BacktestHistoryFilter(arama="ayar-ozel"),
    ) == (kayitlar[1],)


def test_sembol_filtresi_is_eki_olmadan_da_eslesir() -> None:
    kayitlar = (
        kayit("a", semboller=("THYAO.IS",)),
        kayit("b", semboller=("ASELS.IS",)),
    )

    sonuc = gecmis_kayitlarini_filtrele(
        kayitlar,
        BacktestHistoryFilter(semboller=("thyao",)),
    )

    assert sonuc == (kayitlar[0],)


def test_portfoy_kaydi_secili_sembollerden_biriyle_eslesir() -> None:
    portfoy = kayit(
        "p",
        analiz_turu=PORTFOY_ANALIZI,
        baslik="3 Hisselik Portföy Backtest",
        semboller=("THYAO.IS", "TUPRS.IS", "ASELS.IS"),
    )

    sonuc = gecmis_kayitlarini_filtrele(
        (portfoy,),
        BacktestHistoryFilter(semboller=("TUPRS.IS",)),
    )

    assert sonuc == (portfoy,)


def test_tarih_araligi_baslangic_ve_bitisi_dahil_eder() -> None:
    kayitlar = (
        kayit("a", zaman="2026-07-24T23:59:59+03:00"),
        kayit("b", zaman="2026-07-25T12:00:00+03:00"),
        kayit("c", zaman="2026-07-26T00:00:00+03:00"),
        kayit("d", zaman="2026-07-27T00:00:00+03:00"),
    )

    sonuc = gecmis_kayitlarini_filtrele(
        kayitlar,
        BacktestHistoryFilter(
            baslangic_tarihi=date(2026, 7, 25),
            bitis_tarihi=date(2026, 7, 26),
        ),
    )

    assert tuple(k.kayit_kimligi for k in sonuc) == ("b", "c")


def test_gecersiz_kayit_zamani_tarih_filtresinde_atlanir() -> None:
    bozuk = kayit("bozuk", zaman="gecersiz-zaman")

    sonuc = gecmis_kayitlarini_filtrele(
        (bozuk,),
        BacktestHistoryFilter(baslangic_tarihi=date(2026, 1, 1)),
    )

    assert sonuc == ()


def test_birlesik_filtreler_birlikte_uygulanir() -> None:
    kayitlar = (
        kayit("a", zaman="2026-07-25T10:00:00+03:00"),
        kayit(
            "b",
            zaman="2026-07-25T11:00:00+03:00",
            baslik="ASELS.IS özel analiz",
            semboller=("ASELS.IS",),
        ),
        kayit(
            "c",
            zaman="2026-07-24T11:00:00+03:00",
            baslik="ASELS.IS eski analiz",
            semboller=("ASELS.IS",),
        ),
    )

    sonuc = gecmis_kayitlarini_filtrele(
        kayitlar,
        BacktestHistoryFilter(
            arama="özel",
            semboller=("ASELS",),
            baslangic_tarihi=date(2026, 7, 25),
            bitis_tarihi=date(2026, 7, 25),
        ),
    )

    assert sonuc == (kayitlar[1],)


def test_limit_filtreleme_sonrasinda_uygulanir() -> None:
    kayitlar = (
        kayit("a", semboller=("THYAO.IS",)),
        kayit("b", semboller=("ASELS.IS",)),
        kayit("c", semboller=("ASELS.IS",)),
    )

    sonuc = gecmis_kayitlarini_filtrele(
        kayitlar,
        BacktestHistoryFilter(semboller=("ASELS",), limit=1),
    )

    assert tuple(k.kayit_kimligi for k in sonuc) == ("b",)


def test_sembol_ve_tarih_secenekleri_benzersiz_uretilir() -> None:
    kayitlar = (
        kayit("a", zaman="2026-07-25T10:00:00+03:00"),
        kayit(
            "b",
            zaman="2026-07-27T10:00:00+03:00",
            semboller=("ASELS.IS", "THYAO.IS"),
        ),
    )

    assert kayit_sembolleri(kayitlar) == ("ASELS.IS", "THYAO.IS")
    assert kayit_tarih_araligi(kayitlar) == (
        date(2026, 7, 25),
        date(2026, 7, 27),
    )


def test_gecersiz_tarih_araligi_reddedilir() -> None:
    with pytest.raises(ValueError, match="Başlangıç tarihi"):
        BacktestHistoryFilter(
            baslangic_tarihi=date(2026, 7, 26),
            bitis_tarihi=date(2026, 7, 25),
        )


def test_dashboard_arama_sembol_tarih_ve_sonuc_sayisini_gosterir() -> None:
    agac = ast.parse(DASHBOARD_DOSYASI.read_text(encoding="utf-8"))
    metinler = {
        dugum.value
        for dugum in ast.walk(agac)
        if isinstance(dugum, ast.Constant) and isinstance(dugum.value, str)
    }

    assert "Geçmişte ara" in metinler
    assert "Sembol filtresi" in metinler
    assert "Kaydedilme tarihi aralığı" in metinler
    assert any(metin.startswith("Filtre sonucu:") for metin in metinler)
