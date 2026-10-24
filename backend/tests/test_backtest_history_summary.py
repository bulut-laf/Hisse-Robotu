from __future__ import annotations

import ast
from pathlib import Path

import pytest

from backend.app.history.backtest_history import (
    PORTFOY_ANALIZI,
    TEK_HISSE_ANALIZI,
    BacktestHistoryRecord,
)
from backend.app.history.backtest_history_summary import (
    gecmis_ozeti_hesapla,
    gecmis_performans_noktalari,
)


DASHBOARD_DOSYASI = Path(__file__).resolve().parents[1] / "dashboard.py"


def kayit(
    kimlik: str,
    *,
    analiz_turu: str = TEK_HISSE_ANALIZI,
    semboller: tuple[str, ...] = ("THYAO.IS",),
    getiri: float = 50.0,
    dusus: float = 20.0,
    islem: int = 100,
    kar_faktoru: float | None = 1.5,
    kazanma: float | None = 55.0,
) -> BacktestHistoryRecord:
    return BacktestHistoryRecord(
        kayit_kimligi=kimlik,
        analiz_turu=analiz_turu,
        kaydedilme_zamani="2026-07-25T20:00:00+03:00",
        baslik="Test Backtest",
        semboller=semboller,
        donem="2021-01-01 — 2026-01-01",
        tamamlanan_islem_sayisi=islem,
        atlanan_islem_sayisi=20,
        bitis_sermayesi=150_000.0,
        toplam_getiri_yuzde=getiri,
        maksimum_dusus_yuzde=dusus,
        guncel_dusus_yuzde=5.0,
        kar_faktoru=kar_faktoru,
        kazanma_yuzde=kazanma,
        ortalama_sermaye_kullanim_yuzde=None,
        maksimum_pozisyon=None,
        analiz_kimligi=f"analiz-{kimlik}",
        veri_kimligi="veri-1",
        ayar_kimligi="ayar-1",
        dosyalar=(),
    )


def test_bos_gecmis_guvenli_ozet_dondurur() -> None:
    sonuc = gecmis_ozeti_hesapla(())

    assert sonuc.toplam_kayit == 0
    assert sonuc.toplam_tamamlanan_islem == 0
    assert sonuc.medyan_getiri_yuzde is None
    assert sonuc.en_yuksek_getiri_kaydi is None


def test_analiz_turu_sayilari_ayri_hesaplanir() -> None:
    sonuc = gecmis_ozeti_hesapla(
        (
            kayit("tek"),
            kayit(
                "portfoy",
                analiz_turu=PORTFOY_ANALIZI,
                semboller=("THYAO.IS", "ASELS.IS"),
            ),
        )
    )

    assert sonuc.toplam_kayit == 2
    assert sonuc.tek_hisse_kaydi == 1
    assert sonuc.portfoy_kaydi == 1


def test_benzersiz_semboller_buyuk_kucuk_harf_duyarsiz_sayilir() -> None:
    sonuc = gecmis_ozeti_hesapla(
        (
            kayit("a", semboller=("THYAO.IS", "ASELS.IS")),
            kayit("b", semboller=("thyao.is", "TUPRS.IS")),
        )
    )

    assert sonuc.benzersiz_sembol_sayisi == 3


def test_toplam_tamamlanan_islem_hesaplanir() -> None:
    sonuc = gecmis_ozeti_hesapla(
        (kayit("a", islem=80), kayit("b", islem=114))
    )

    assert sonuc.toplam_tamamlanan_islem == 194


def test_getiri_ve_dusus_ortalama_medyanlari_hesaplanir() -> None:
    sonuc = gecmis_ozeti_hesapla(
        (
            kayit("a", getiri=10.0, dusus=12.0),
            kayit("b", getiri=30.0, dusus=20.0),
            kayit("c", getiri=80.0, dusus=40.0),
        )
    )

    assert sonuc.ortalama_getiri_yuzde == pytest.approx(40.0)
    assert sonuc.medyan_getiri_yuzde == pytest.approx(30.0)
    assert sonuc.ortalama_maksimum_dusus_yuzde == pytest.approx(24.0)
    assert sonuc.medyan_maksimum_dusus_yuzde == pytest.approx(20.0)


def test_istege_bagli_ortalamalar_none_degerleri_atlar() -> None:
    sonuc = gecmis_ozeti_hesapla(
        (
            kayit("a", kar_faktoru=1.5, kazanma=55.0),
            kayit("b", kar_faktoru=None, kazanma=None),
            kayit("c", kar_faktoru=2.5, kazanma=65.0),
        )
    )

    assert sonuc.ortalama_kar_faktoru == pytest.approx(2.0)
    assert sonuc.ortalama_kazanma_yuzde == pytest.approx(60.0)


def test_lider_kayitlar_getiri_ve_dususe_gore_belirlenir() -> None:
    yuksek = kayit("yuksek", getiri=90.0, dusus=30.0)
    dusuk_risk = kayit("dusuk-risk", getiri=40.0, dusus=10.0)

    sonuc = gecmis_ozeti_hesapla((dusuk_risk, yuksek))

    assert sonuc.en_yuksek_getiri_kaydi == yuksek
    assert sonuc.en_dusuk_dusus_kaydi == dusuk_risk


def test_performans_noktalari_grafik_alanlarini_uretir() -> None:
    portfoy = kayit(
        "portfoy-kaydi",
        analiz_turu=PORTFOY_ANALIZI,
        semboller=("THYAO.IS", "ASELS.IS"),
        getiri=120.0,
        dusus=25.0,
        islem=200,
    )

    sonuc = gecmis_performans_noktalari((portfoy,))

    assert len(sonuc) == 1
    assert sonuc[0].analiz_turu == "Portföy"
    assert sonuc[0].etiket.startswith("THYAO.IS, ASELS.IS")
    assert sonuc[0].toplam_getiri_yuzde == 120.0
    assert sonuc[0].tamamlanan_islem_sayisi == 200


def test_performans_noktalari_girdi_sirasini_korur() -> None:
    sonuc = gecmis_performans_noktalari((kayit("b"), kayit("a")))

    assert tuple(nokta.kayit_kimligi for nokta in sonuc) == ("b", "a")


def test_metin_koleksiyon_olarak_kabul_edilmez() -> None:
    with pytest.raises(TypeError, match="koleksiyon"):
        gecmis_ozeti_hesapla("kayitlar")


def test_gecersiz_kayit_turu_reddedilir() -> None:
    with pytest.raises(TypeError, match="BacktestHistoryRecord"):
        gecmis_performans_noktalari((object(),))


def test_dashboard_ozet_ve_risk_getiri_gorunumunu_icerir() -> None:
    agac = ast.parse(DASHBOARD_DOSYASI.read_text(encoding="utf-8"))
    metinler = {
        dugum.value
        for dugum in ast.walk(agac)
        if isinstance(dugum, ast.Constant) and isinstance(dugum.value, str)
    }

    assert "Geçmiş performans özeti" in metinler
    assert "Risk-getiri görünümü" in metinler
    assert "Medyan getiri" in metinler
    assert "Medyan maks. düşüş" in metinler

    scatter_cagrilari = [
        dugum
        for dugum in ast.walk(agac)
        if isinstance(dugum, ast.Call)
        and isinstance(dugum.func, ast.Attribute)
        and dugum.func.attr == "scatter_chart"
    ]
    assert scatter_cagrilari
    width_degerleri = {
        anahtar.arg: anahtar.value.value
        for anahtar in scatter_cagrilari[0].keywords
        if anahtar.arg is not None
        and isinstance(anahtar.value, ast.Constant)
    }
    assert width_degerleri["width"] == "stretch"
