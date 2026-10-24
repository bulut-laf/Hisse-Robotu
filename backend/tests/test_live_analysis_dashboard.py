from __future__ import annotations

import ast
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.data.multi_timeframe_data import MultiTimeframeDataError
from backend.app.ui.live_analysis_dashboard import (
    LiveAnalysisDashboardError,
    LiveAnalysisDashboardService,
    LiveAnalysisRequest,
    OpenPositionDashboardRequest,
    OpenPositionDashboardService,
)


DASHBOARD_DOSYASI = Path(__file__).resolve().parents[1] / "dashboard.py"


def test_guncel_analiz_istegi_bist_sembolunu_normalize_eder() -> None:
    istek = LiveAnalysisRequest(" thyao ")

    assert istek.sembol == "THYAO.IS"


def test_guncel_analiz_istegi_pozitif_sermaye_gerektirir() -> None:
    with pytest.raises(ValueError, match="Sermaye pozitif"):
        LiveAnalysisRequest("THYAO", sermaye=0)


def test_guncel_analiz_istegi_gecerli_risk_orani_gerektirir() -> None:
    with pytest.raises(ValueError, match="Azami risk oranı"):
        LiveAnalysisRequest("THYAO", azami_risk_orani=0)

    with pytest.raises(ValueError, match="Azami risk oranı"):
        LiveAnalysisRequest("THYAO", azami_risk_orani=1.01)


def test_guncel_analiz_servisi_ayni_paketi_motorlara_iletir() -> None:
    paket = object()
    teknik = object()
    plan = object()
    cagrilar: list[tuple[str, object]] = []

    def veri_getirici(sembol: str) -> object:
        cagrilar.append(("veri", sembol))
        return paket

    def teknik_motoru(gelen_paket: object) -> object:
        cagrilar.append(("teknik", gelen_paket))
        return teknik

    def plan_motoru(**kwargs: object) -> object:
        cagrilar.append(("plan_paket", kwargs["paket"]))
        cagrilar.append(("plan_teknik", kwargs["teknik_teyit"]))
        cagrilar.append(("sermaye", kwargs["sermaye"]))
        cagrilar.append(("risk", kwargs["azami_risk_orani"]))
        return plan

    sonuc = LiveAnalysisDashboardService(
        veri_getirici=veri_getirici,
        teknik_motoru=teknik_motoru,
        plan_motoru=plan_motoru,
    ).calistir(
        LiveAnalysisRequest(
            "THYAO",
            sermaye=250_000,
            azami_risk_orani=0.02,
        )
    )

    assert sonuc.paket is paket
    assert sonuc.teknik_teyit is teknik
    assert sonuc.islem_plani is plan
    assert cagrilar == [
        ("veri", "THYAO.IS"),
        ("teknik", paket),
        ("plan_paket", paket),
        ("plan_teknik", teknik),
        ("sermaye", 250_000),
        ("risk", 0.02),
    ]


def test_guncel_analiz_servisi_veri_hatasini_ekran_hatasina_cevirir() -> None:
    def hatali_veri_getirici(_sembol: str) -> object:
        raise MultiTimeframeDataError("Veri bulunamadı")

    servis = LiveAnalysisDashboardService(veri_getirici=hatali_veri_getirici)

    with pytest.raises(LiveAnalysisDashboardError, match="Veri bulunamadı"):
        servis.calistir(LiveAnalysisRequest("THYAO"))


def test_acik_pozisyon_istegi_domain_modelini_olusturur() -> None:
    istek = OpenPositionDashboardRequest(
        sembol="thyao",
        giris_tarihi=date(2026, 7, 1),
        giris_fiyati=300,
        lot_sayisi=100,
        ilk_stop=286.5,
        hedef_1=327,
        hedef_2=354,
        mevcut_stop=309.25,
        hedef_1_gerceklesti=True,
    )

    pozisyon = istek.pozisyon_olustur()

    assert istek.sembol == "THYAO.IS"
    assert pozisyon.giris_tarihi == date(2026, 7, 1)
    assert pozisyon.giris_fiyati == 300.0
    assert pozisyon.lot_sayisi == 100
    assert pozisyon.ilk_stop == 286.5
    assert pozisyon.mevcut_stop == 309.25
    assert pozisyon.hedef_1_gerceklesti is True


def test_acik_pozisyon_servisi_ayni_paket_ve_teknik_teyidi_kullanir() -> None:
    paket = object()
    teknik = object()
    izleme_sonucu = SimpleNamespace(durum="Aktif")
    yakalanan: dict[str, object] = {}

    def veri_getirici(sembol: str) -> object:
        yakalanan["sembol"] = sembol
        return paket

    def teknik_motoru(gelen_paket: object) -> object:
        yakalanan["teknik_paket"] = gelen_paket
        return teknik

    def izleme_motoru(**kwargs: object) -> object:
        yakalanan.update(kwargs)
        return izleme_sonucu

    istek = OpenPositionDashboardRequest(
        sembol="THYAO",
        giris_tarihi="2026-07-01",
        giris_fiyati=300,
        lot_sayisi=100,
        ilk_stop=286.5,
        hedef_1=327,
        hedef_2=354,
    )
    sonuc = OpenPositionDashboardService(
        veri_getirici=veri_getirici,
        teknik_motoru=teknik_motoru,
        izleme_motoru=izleme_motoru,
    ).calistir(istek)

    assert sonuc is izleme_sonucu
    assert yakalanan["sembol"] == "THYAO.IS"
    assert yakalanan["teknik_paket"] is paket
    assert yakalanan["paket"] is paket
    assert yakalanan["teknik_teyit"] is teknik
    assert yakalanan["pozisyon"].giris_fiyati == 300.0


def test_acik_pozisyon_servisi_deger_hatasini_ekran_hatasina_cevirir() -> None:
    def izleme_motoru(**_kwargs: object) -> object:
        raise ValueError("Stop girişin altında olmalıdır")

    servis = OpenPositionDashboardService(
        veri_getirici=lambda _sembol: object(),
        teknik_motoru=lambda _paket: object(),
        izleme_motoru=izleme_motoru,
    )
    istek = OpenPositionDashboardRequest(
        sembol="THYAO",
        giris_tarihi="2026-07-01",
        giris_fiyati=300,
        lot_sayisi=100,
        ilk_stop=301,
        hedef_1=327,
        hedef_2=354,
    )

    with pytest.raises(
        LiveAnalysisDashboardError,
        match="Stop girişin altında",
    ):
        servis.calistir(istek)


def test_dashboard_yeni_analiz_modlarini_sunar() -> None:
    kaynak = DASHBOARD_DOSYASI.read_text(encoding="utf-8")

    assert '"Güncel Teknik Analiz"' in kaynak
    assert '"Açık Pozisyon İzleme"' in kaynak


def test_dashboard_yeni_form_ve_sonuc_fonksiyonlarini_icerir() -> None:
    agac = ast.parse(DASHBOARD_DOSYASI.read_text(encoding="utf-8"))
    fonksiyonlar = {
        dugum.name
        for dugum in agac.body
        if isinstance(dugum, ast.FunctionDef)
    }

    assert {
        "guncel_teknik_analiz_formu",
        "guncel_analiz_sonucu_goster",
        "acik_pozisyon_izleme_formu",
        "acik_pozisyon_sonucu_goster",
    }.issubset(fonksiyonlar)


def test_dashboard_guncel_analizde_uc_sekmeyi_gosterir() -> None:
    kaynak = DASHBOARD_DOSYASI.read_text(encoding="utf-8")

    assert '"Zaman dilimleri"' in kaynak
    assert '"Teknik teyit"' in kaynak
    assert '"İşlem planı"' in kaynak


def test_dashboard_acik_pozisyonda_tam_cikis_degerlendirmesini_gosterir() -> None:
    kaynak = DASHBOARD_DOSYASI.read_text(encoding="utf-8")

    assert "Kâr alma değerlendirmesi" in kaynak
    assert '"Tam çıkış"' in kaynak


def test_dashboard_metrik_metinlerini_satirlayarak_tam_gosterir() -> None:
    kaynak = DASHBOARD_DOSYASI.read_text(encoding="utf-8")

    assert 'white-space: normal !important;' in kaynak
    assert 'text-overflow: clip !important;' in kaynak
    assert 'overflow: visible !important;' in kaynak


def test_dashboard_islem_planinda_iki_hedef_kartini_gosterir() -> None:
    kaynak = DASHBOARD_DOSYASI.read_text(encoding="utf-8")

    assert '("Hedef 1", opsiyonel_fiyat_yaz(plan.hedef_1))' in kaynak
    assert '("Hedef 2", opsiyonel_fiyat_yaz(plan.hedef_2))' in kaynak


def test_dashboard_zaman_tablosunda_tarih_saat_yardimcisini_kullanir() -> None:
    kaynak = DASHBOARD_DOSYASI.read_text(encoding="utf-8")

    assert '"Son tarih": tarih_saat_yaz(zaman.son_zaman)' in kaynak


def test_dashboard_tarih_saat_yardimcisi_gece_yarisini_gizler() -> None:
    agac = ast.parse(DASHBOARD_DOSYASI.read_text(encoding="utf-8"))
    fonksiyon = next(
        dugum
        for dugum in agac.body
        if isinstance(dugum, ast.FunctionDef) and dugum.name == "tarih_saat_yaz"
    )
    modul = ast.Module(body=[fonksiyon], type_ignores=[])
    kapsam = {"date": date, "datetime": __import__("datetime").datetime}
    exec(compile(modul, str(DASHBOARD_DOSYASI), "exec"), kapsam)

    tarih_saat_yaz = kapsam["tarih_saat_yaz"]
    assert tarih_saat_yaz("2026-07-24 00:00:00") == "2026-07-24"
    assert tarih_saat_yaz("2026-07-24 17:30:00") == "2026-07-24 17:30:00"
