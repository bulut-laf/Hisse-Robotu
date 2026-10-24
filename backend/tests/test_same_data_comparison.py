from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from backend.app.backtest.same_data_comparison import (
    BAZ_ANALIZ,
    DUSUK_DAHA_IYI,
    KARSILASTIRMA_ANALIZI,
    SameDataComparisonError,
    SameDataComparisonService,
)
from backend.app.ui.backtest_dashboard import (
    DashboardBacktestRequest,
    DashboardResult,
    DashboardSummary,
)


def fiyat_verisi() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [10.0, 11.0, 12.0],
            "High": [11.0, 12.0, 13.0],
            "Low": [9.0, 10.0, 11.0],
            "Close": [10.5, 11.5, 12.5],
            "Volume": [1000.0, 1100.0, 1200.0],
        },
        index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
    )


def sonuc(istek: DashboardBacktestRequest, veri_kimligi: str = "veri123") -> DashboardResult:
    yuksek_skor = istek.minimum_skor >= 55
    return DashboardResult(
        ozet=DashboardSummary(
            sembol=istek.sembol,
            fiyat_donemi="2026-01-01 — 2026-01-03",
            fiyat_bar_sayisi=3,
            analiz_kimligi=f"analiz{istek.minimum_skor}",
            veri_kimligi=veri_kimligi,
            ayar_kimligi=istek.profil_olustur().ayar_kimligi,
            tamamlanan_islem_sayisi=8 if yuksek_skor else 10,
            atlanan_sinyal_sayisi=12 if yuksek_skor else 10,
            kazanma_yuzde=62.0 if yuksek_skor else 55.0,
            toplam_getiri_yuzde=80.0 if yuksek_skor else 100.0,
            bitis_sermayesi=180_000.0 if yuksek_skor else 200_000.0,
            maksimum_dusus_yuzde=20.0 if yuksek_skor else 25.0,
            guncel_dusus_yuzde=5.0 if yuksek_skor else 8.0,
            kar_faktoru=1.9 if yuksek_skor else 1.7,
            al_tut_getiri_yuzde=90.0,
        ),
        islemler=(),
    )


class SahteDashboard:
    def __init__(self, veri: pd.DataFrame, *, veri_kimligi: str = "veri123") -> None:
        self.veri = veri
        self.veri_kimligi = veri_kimligi

    def calistir(self, istek: DashboardBacktestRequest) -> DashboardResult:
        assert len(self.veri) == 3
        return sonuc(istek, self.veri_kimligi)


def istek(minimum_skor: int = 50) -> DashboardBacktestRequest:
    return DashboardBacktestRequest(
        sembol="THYAO",
        islem_gunu=1253,
        indirme_donemi="5y",
        minimum_skor=minimum_skor,
    )


def test_fiyat_verisi_yalnizca_bir_kez_alinir() -> None:
    cagri = 0

    def getirici(**_: object) -> pd.DataFrame:
        nonlocal cagri
        cagri += 1
        return fiyat_verisi()

    servis = SameDataComparisonService(
        veri_getirici=getirici,
        dashboard_uretici=lambda veri: SahteDashboard(veri),
    )
    servis.calistir(istek(50), istek(55))

    assert cagri == 1


def test_iki_analiz_ayni_veri_kimligini_kullanir() -> None:
    servis = SameDataComparisonService(
        veri_getirici=lambda **_: fiyat_verisi(),
        dashboard_uretici=lambda veri: SahteDashboard(veri),
    )

    rapor = servis.calistir(istek(50), istek(55))

    assert rapor.veri_kimligi == "veri123"
    assert rapor.baz_sonuc.ozet.veri_kimligi == rapor.karsilastirma_sonucu.ozet.veri_kimligi
    assert rapor.ayar_kimlikleri_farkli is True


def test_anlik_goruntu_her_calistirmaya_ayri_kopya_verir() -> None:
    kimlikler: list[int] = []

    def uretici(veri: pd.DataFrame) -> SahteDashboard:
        kimlikler.append(id(veri))
        veri.iloc[0, 0] = 999.0
        return SahteDashboard(veri)

    servis = SameDataComparisonService(
        veri_getirici=lambda **_: fiyat_verisi(),
        dashboard_uretici=uretici,
    )
    servis.calistir(istek(50), istek(55))

    assert len(set(kimlikler)) == 2


def test_ayni_sembol_zorunludur() -> None:
    servis = SameDataComparisonService(
        veri_getirici=lambda **_: fiyat_verisi(),
        dashboard_uretici=lambda veri: SahteDashboard(veri),
    )

    with pytest.raises(ValueError, match="semboller aynı"):
        servis.calistir(istek(50), replace(istek(55), sembol="ASELS.IS"))


def test_ayni_islem_gunu_siniri_zorunludur() -> None:
    servis = SameDataComparisonService(
        veri_getirici=lambda **_: fiyat_verisi(),
        dashboard_uretici=lambda veri: SahteDashboard(veri),
    )

    with pytest.raises(ValueError, match="işlem günü"):
        servis.calistir(istek(50), replace(istek(55), islem_gunu=1000))


def test_ayni_indirme_donemi_zorunludur() -> None:
    servis = SameDataComparisonService(
        veri_getirici=lambda **_: fiyat_verisi(),
        dashboard_uretici=lambda veri: SahteDashboard(veri),
    )

    with pytest.raises(ValueError, match="indirme dönemi"):
        servis.calistir(istek(50), replace(istek(55), indirme_donemi="2y"))


def test_ayarlar_farkli_olmalidir() -> None:
    servis = SameDataComparisonService(
        veri_getirici=lambda **_: fiyat_verisi(),
        dashboard_uretici=lambda veri: SahteDashboard(veri),
    )

    with pytest.raises(ValueError, match="en az biri farklı"):
        servis.calistir(istek(50), istek(50))


def test_bos_veri_reddedilir() -> None:
    servis = SameDataComparisonService(
        veri_getirici=lambda **_: pd.DataFrame(),
        dashboard_uretici=lambda veri: SahteDashboard(veri),
    )

    with pytest.raises(SameDataComparisonError, match="boş"):
        servis.calistir(istek(50), istek(55))


def test_farkli_veri_kimligi_reddedilir() -> None:
    sira = 0

    def uretici(veri: pd.DataFrame) -> SahteDashboard:
        nonlocal sira
        sira += 1
        return SahteDashboard(veri, veri_kimligi=f"veri{sira}")

    servis = SameDataComparisonService(
        veri_getirici=lambda **_: fiyat_verisi(),
        dashboard_uretici=uretici,
    )

    with pytest.raises(SameDataComparisonError, match="aynı veri kimliğini"):
        servis.calistir(istek(50), istek(55))


def test_metrikler_farki_ve_lideri_dogru_hesaplar() -> None:
    servis = SameDataComparisonService(
        veri_getirici=lambda **_: fiyat_verisi(),
        dashboard_uretici=lambda veri: SahteDashboard(veri),
    )

    rapor = servis.calistir(istek(50), istek(55))
    getiri = next(m for m in rapor.metrikler if m.anahtar == "toplam_getiri_yuzde")
    dusus = next(m for m in rapor.metrikler if m.anahtar == "maksimum_dusus_yuzde")

    assert getiri.fark == pytest.approx(-20.0)
    assert getiri.lider == BAZ_ANALIZ
    assert dusus.iyilik_yonu == DUSUK_DAHA_IYI
    assert dusus.lider == KARSILASTIRMA_ANALIZI
