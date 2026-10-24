from __future__ import annotations

import ast
from pathlib import Path

import pytest

from backend.app.history.backtest_history import (
    TEK_HISSE_ANALIZI,
    BacktestHistoryRecord,
)
from backend.app.history.backtest_history_pagination import (
    SIRALAMA_DUSUS_ARTAN,
    SIRALAMA_EN_ESKI,
    SIRALAMA_EN_YENI,
    SIRALAMA_GETIRI_AZALAN,
    SIRALAMA_SEMBOL_ARTAN,
    gecmis_kayitlarini_sayfala,
    gecmis_kayitlarini_sirala,
)


DASHBOARD_DOSYASI = Path(__file__).resolve().parents[1] / "dashboard.py"


def kayit(
    kimlik: str,
    *,
    zaman: str = "2026-07-25T20:00:00+03:00",
    sembol: str = "THYAO.IS",
    getiri: float = 50.0,
    dusus: float = 20.0,
) -> BacktestHistoryRecord:
    return BacktestHistoryRecord(
        kayit_kimligi=kimlik,
        analiz_turu=TEK_HISSE_ANALIZI,
        kaydedilme_zamani=zaman,
        baslik=f"{sembol} · Tek Hisse Backtest",
        semboller=(sembol,),
        donem="2021-01-01 — 2026-01-01",
        tamamlanan_islem_sayisi=100,
        atlanan_islem_sayisi=20,
        bitis_sermayesi=150_000.0,
        toplam_getiri_yuzde=getiri,
        maksimum_dusus_yuzde=dusus,
        guncel_dusus_yuzde=5.0,
        kar_faktoru=1.5,
        kazanma_yuzde=55.0,
        ortalama_sermaye_kullanim_yuzde=None,
        maksimum_pozisyon=None,
        analiz_kimligi="analiz-1",
        veri_kimligi="veri-1",
        ayar_kimligi="ayar-1",
        dosyalar=(),
    )


def kimlikler(kayitlar: tuple[BacktestHistoryRecord, ...]) -> tuple[str, ...]:
    return tuple(kayit.kayit_kimligi for kayit in kayitlar)


def test_en_yeni_kayit_once_siralanir() -> None:
    kayitlar = (
        kayit("eski", zaman="2026-07-24T10:00:00+03:00"),
        kayit("yeni", zaman="2026-07-26T10:00:00+03:00"),
    )

    sonuc = gecmis_kayitlarini_sirala(kayitlar, SIRALAMA_EN_YENI)

    assert kimlikler(sonuc) == ("yeni", "eski")


def test_en_eski_kayit_once_siralanir() -> None:
    kayitlar = (
        kayit("yeni", zaman="2026-07-26T10:00:00+03:00"),
        kayit("eski", zaman="2026-07-24T10:00:00+03:00"),
    )

    sonuc = gecmis_kayitlarini_sirala(kayitlar, SIRALAMA_EN_ESKI)

    assert kimlikler(sonuc) == ("eski", "yeni")


def test_getiri_yuksekten_dusuge_siralanir() -> None:
    kayitlar = (
        kayit("dusuk", getiri=10.0),
        kayit("yuksek", getiri=80.0),
        kayit("orta", getiri=40.0),
    )

    sonuc = gecmis_kayitlarini_sirala(
        kayitlar,
        SIRALAMA_GETIRI_AZALAN,
    )

    assert kimlikler(sonuc) == ("yuksek", "orta", "dusuk")


def test_maksimum_dusus_dusukten_yuksege_siralanir() -> None:
    kayitlar = (
        kayit("riskli", dusus=45.0),
        kayit("dusuk-risk", dusus=12.0),
        kayit("orta", dusus=25.0),
    )

    sonuc = gecmis_kayitlarini_sirala(
        kayitlar,
        SIRALAMA_DUSUS_ARTAN,
    )

    assert kimlikler(sonuc) == ("dusuk-risk", "orta", "riskli")


def test_sembol_alfabetik_siralanir() -> None:
    kayitlar = (
        kayit("t", sembol="TUPRS.IS"),
        kayit("a", sembol="ASELS.IS"),
        kayit("h", sembol="THYAO.IS"),
    )

    sonuc = gecmis_kayitlarini_sirala(
        kayitlar,
        SIRALAMA_SEMBOL_ARTAN,
    )

    assert kimlikler(sonuc) == ("a", "h", "t")


def test_gecersiz_zaman_tarih_siralamasinda_sona_alinir() -> None:
    kayitlar = (
        kayit("bozuk", zaman="gecersiz"),
        kayit("gecerli", zaman="2026-07-25T10:00:00+03:00"),
    )

    yeni = gecmis_kayitlarini_sirala(kayitlar, SIRALAMA_EN_YENI)
    eski = gecmis_kayitlarini_sirala(kayitlar, SIRALAMA_EN_ESKI)

    assert kimlikler(yeni) == ("gecerli", "bozuk")
    assert kimlikler(eski) == ("gecerli", "bozuk")


def test_desteklenmeyen_siralama_reddedilir() -> None:
    with pytest.raises(ValueError, match="Desteklenmeyen"):
        gecmis_kayitlarini_sirala((kayit("a"),), "bilinmeyen")


def test_ilk_sayfa_dogru_kayit_araligini_dondurur() -> None:
    kayitlar = tuple(kayit(str(i)) for i in range(1, 8))

    sonuc = gecmis_kayitlarini_sayfala(
        kayitlar,
        sayfa=1,
        sayfa_boyutu=3,
    )

    assert kimlikler(sonuc.kayitlar) == ("1", "2", "3")
    assert sonuc.toplam_kayit == 7
    assert sonuc.toplam_sayfa == 3
    assert (sonuc.ilk_sira, sonuc.son_sira) == (1, 3)


def test_son_sayfa_kismi_kayitlari_dondurur() -> None:
    kayitlar = tuple(kayit(str(i)) for i in range(1, 8))

    sonuc = gecmis_kayitlarini_sayfala(
        kayitlar,
        sayfa=3,
        sayfa_boyutu=3,
    )

    assert kimlikler(sonuc.kayitlar) == ("7",)
    assert (sonuc.ilk_sira, sonuc.son_sira) == (7, 7)


def test_tasan_sayfa_istegi_son_sayfaya_cekilir() -> None:
    kayitlar = tuple(kayit(str(i)) for i in range(1, 6))

    sonuc = gecmis_kayitlarini_sayfala(
        kayitlar,
        sayfa=99,
        sayfa_boyutu=2,
    )

    assert sonuc.sayfa == 3
    assert kimlikler(sonuc.kayitlar) == ("5",)


def test_bos_koleksiyon_guvenli_birinci_sayfa_dondurur() -> None:
    sonuc = gecmis_kayitlarini_sayfala((), sayfa=1, sayfa_boyutu=10)

    assert sonuc.kayitlar == ()
    assert sonuc.toplam_kayit == 0
    assert sonuc.toplam_sayfa == 1
    assert (sonuc.ilk_sira, sonuc.son_sira) == (0, 0)


def test_gecersiz_sayfa_degerleri_reddedilir() -> None:
    with pytest.raises(ValueError, match="sayfa numarası"):
        gecmis_kayitlarini_sayfala((kayit("a"),), sayfa=0, sayfa_boyutu=10)
    with pytest.raises(ValueError, match="sayfa boyutu"):
        gecmis_kayitlarini_sayfala((kayit("a"),), sayfa=1, sayfa_boyutu=0)


def test_dashboard_siralama_ve_sayfalama_kontrollerini_gosterir() -> None:
    agac = ast.parse(DASHBOARD_DOSYASI.read_text(encoding="utf-8"))
    metinler = {
        dugum.value
        for dugum in ast.walk(agac)
        if isinstance(dugum, ast.Constant) and isinstance(dugum.value, str)
    }

    assert "Sıralama" in metinler
    assert "Sayfa başına kayıt" in metinler
    assert "Sayfa" in metinler
    assert "En yeni kayıt" in metinler
    assert "Toplam getiri: yüksekten düşüğe" in metinler
