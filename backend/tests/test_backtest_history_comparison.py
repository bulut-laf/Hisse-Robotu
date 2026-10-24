from __future__ import annotations

from dataclasses import replace

import pytest

from backend.app.history.backtest_history import (
    PORTFOY_ANALIZI,
    TEK_HISSE_ANALIZI,
    BacktestHistoryRecord,
)
from backend.app.history.backtest_history_comparison import (
    DUSUK_DAHA_IYI,
    ESIT,
    IKINCI_KAYIT,
    NOTR,
    YUKSEK_DAHA_IYI,
    BacktestHistoryComparisonError,
    gecmis_kayitlarini_karsilastir,
)


def kayit(
    kimlik: str,
    *,
    analiz_turu: str = TEK_HISSE_ANALIZI,
    semboller: tuple[str, ...] = ("THYAO.IS",),
    donem: str = "2021-01-01 — 2026-01-01",
    veri: str = "veri-1",
    ayar: str = "ayar-1",
    bitis: float = 150_000.0,
    getiri: float = 50.0,
    maksimum_dusus: float = 20.0,
    guncel_dusus: float = 5.0,
    kar_faktoru: float | None = 1.5,
    kazanma: float | None = 55.0,
    ortalama_kullanim: float | None = None,
    maksimum_pozisyon: int | None = None,
) -> BacktestHistoryRecord:
    return BacktestHistoryRecord(
        kayit_kimligi=kimlik,
        analiz_turu=analiz_turu,
        kaydedilme_zamani="2026-07-25T20:00:00+03:00",
        baslik="Test kaydı",
        semboller=semboller,
        donem=donem,
        tamamlanan_islem_sayisi=100,
        atlanan_islem_sayisi=20,
        bitis_sermayesi=bitis,
        toplam_getiri_yuzde=getiri,
        maksimum_dusus_yuzde=maksimum_dusus,
        guncel_dusus_yuzde=guncel_dusus,
        kar_faktoru=kar_faktoru,
        kazanma_yuzde=kazanma,
        ortalama_sermaye_kullanim_yuzde=ortalama_kullanim,
        maksimum_pozisyon=maksimum_pozisyon,
        analiz_kimligi="analiz",
        veri_kimligi=veri,
        ayar_kimligi=ayar,
        dosyalar=(),
    )


def test_ayni_kayit_kendisiyle_karsilastirilamaz() -> None:
    ilk = kayit("a")

    with pytest.raises(BacktestHistoryComparisonError, match="kendisiyle"):
        gecmis_kayitlarini_karsilastir(ilk, ilk)


def test_farkli_analiz_turleri_karsilastirilamaz() -> None:
    ilk = kayit("a")
    ikinci = kayit(
        "b",
        analiz_turu=PORTFOY_ANALIZI,
        semboller=("THYAO.IS", "ASELS.IS"),
        kazanma=None,
        ortalama_kullanim=50.0,
        maksimum_pozisyon=2,
    )

    with pytest.raises(BacktestHistoryComparisonError, match="aynı tür"):
        gecmis_kayitlarini_karsilastir(ilk, ikinci)


def test_ayni_veri_ve_semboller_dogrudan_karsilastirilabilir() -> None:
    sonuc = gecmis_kayitlarini_karsilastir(
        kayit("a", ayar="ayar-1"),
        kayit("b", ayar="ayar-2"),
    )

    assert sonuc.dogrudan_karsilastirilabilir is True
    assert sonuc.veri_ayni is True
    assert sonuc.ayarlar_ayni is False
    assert sonuc.uyarilar == ()


def test_farkli_veri_kimligi_uyari_uretir() -> None:
    sonuc = gecmis_kayitlarini_karsilastir(
        kayit("a", veri="veri-1"),
        kayit("b", veri="veri-2"),
    )

    assert sonuc.dogrudan_karsilastirilabilir is False
    assert any("Veri kimlikleri farklı" in uyari for uyari in sonuc.uyarilar)


def test_farkli_semboller_ve_donem_uyari_uretir() -> None:
    sonuc = gecmis_kayitlarini_karsilastir(
        kayit("a"),
        kayit("b", semboller=("ASELS.IS",), donem="2022 — 2026"),
    )

    assert sonuc.semboller_ayni is False
    assert sonuc.donem_ayni is False
    assert len(sonuc.uyarilar) >= 2


def test_toplam_getiride_yuksek_deger_liderdir() -> None:
    sonuc = gecmis_kayitlarini_karsilastir(
        kayit("a", getiri=50.0),
        kayit("b", getiri=70.0),
    )
    metrik = sonuc.metrik("toplam_getiri_yuzde")

    assert metrik is not None
    assert metrik.fark == pytest.approx(20.0)
    assert metrik.iyilik_yonu == YUKSEK_DAHA_IYI
    assert metrik.lider == IKINCI_KAYIT


def test_maksimum_dususte_dusuk_deger_liderdir() -> None:
    sonuc = gecmis_kayitlarini_karsilastir(
        kayit("a", maksimum_dusus=30.0),
        kayit("b", maksimum_dusus=20.0),
    )
    metrik = sonuc.metrik("maksimum_dusus_yuzde")

    assert metrik is not None
    assert metrik.fark == pytest.approx(-10.0)
    assert metrik.iyilik_yonu == DUSUK_DAHA_IYI
    assert metrik.lider == IKINCI_KAYIT


def test_islem_sayisi_notr_metriktir() -> None:
    ilk = kayit("a")
    ikinci = replace(kayit("b"), tamamlanan_islem_sayisi=120)
    metrik = gecmis_kayitlarini_karsilastir(ilk, ikinci).metrik(
        "tamamlanan_islem_sayisi"
    )

    assert metrik is not None
    assert metrik.iyilik_yonu == NOTR
    assert metrik.lider == ESIT


def test_getiri_dusus_orani_hesaplanir() -> None:
    sonuc = gecmis_kayitlarini_karsilastir(
        kayit("a", getiri=50.0, maksimum_dusus=25.0),
        kayit("b", getiri=60.0, maksimum_dusus=20.0),
    )
    metrik = sonuc.metrik("getiri_dusus_orani")

    assert metrik is not None
    assert metrik.ilk_deger == pytest.approx(2.0)
    assert metrik.ikinci_deger == pytest.approx(3.0)


def test_kar_faktoru_eksikse_metrik_gosterilmez() -> None:
    sonuc = gecmis_kayitlarini_karsilastir(
        kayit("a", kar_faktoru=None),
        kayit("b", kar_faktoru=1.6),
    )

    assert sonuc.metrik("kar_faktoru") is None


def test_tek_hisse_kazanma_orani_metrigi_eklenir() -> None:
    sonuc = gecmis_kayitlarini_karsilastir(
        kayit("a", kazanma=50.0),
        kayit("b", kazanma=60.0),
    )

    assert sonuc.metrik("kazanma_yuzde") is not None


def test_portfoy_kullanim_ve_pozisyon_metrikleri_eklenir() -> None:
    ilk = kayit(
        "a",
        analiz_turu=PORTFOY_ANALIZI,
        semboller=("THYAO.IS", "ASELS.IS"),
        kazanma=None,
        ortalama_kullanim=45.0,
        maksimum_pozisyon=2,
    )
    ikinci = kayit(
        "b",
        analiz_turu=PORTFOY_ANALIZI,
        semboller=("THYAO.IS", "ASELS.IS"),
        kazanma=None,
        ortalama_kullanim=55.0,
        maksimum_pozisyon=3,
    )
    sonuc = gecmis_kayitlarini_karsilastir(ilk, ikinci)

    assert sonuc.metrik("ortalama_sermaye_kullanim_yuzde") is not None
    assert sonuc.metrik("maksimum_pozisyon") is not None
