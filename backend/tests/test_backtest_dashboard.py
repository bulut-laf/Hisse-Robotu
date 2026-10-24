from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from backend.app.ui.backtest_dashboard import (
    BacktestDashboardService,
    DashboardBacktestRequest,
    DashboardTradeRow,
)


class SahteBacktestServisi:
    def __init__(self, rapor: object) -> None:
        self.rapor = rapor
        self.sembol: str | None = None
        self.yapilandirma: object | None = None

    def calistir(
        self,
        sembol: str,
        yapilandirma: object | None = None,
    ) -> object:
        self.sembol = sembol
        self.yapilandirma = yapilandirma
        return self.rapor


def sahte_islem() -> SimpleNamespace:
    return SimpleNamespace(
        sinyal_tarihi=date(2026, 1, 2),
        giris_tarihi=date(2026, 1, 5),
        cikis_tarihi=date(2026, 1, 12),
        skor=72,
        giris_fiyati=100.0,
        cikis_fiyati=110.0,
        net_getiri_orani=0.0978,
        elde_tutulan_bar=6,
        cikis_nedeni="Hedef",
    )


def sahte_rapor(
    *,
    gunluk_var: bool = True,
    baglam_var: bool = True,
    benchmark_var: bool = True,
) -> SimpleNamespace:
    islemler = (sahte_islem(),)
    metrikler = SimpleNamespace(
        kazanma_orani=1.0,
        kar_faktoru=2.5,
    )
    backtest_sonucu = SimpleNamespace(
        metrikler=metrikler,
        islemler=islemler,
        tamamlanan_islem_sayisi=1,
        atlanan_sinyal_sayisi=3,
    )
    ozsermaye = SimpleNamespace(
        toplam_bilesik_getiri_orani=0.25,
        bitis_sermayesi=125_000.0,
        maksimum_dusus_orani=0.18,
    )
    gunluk = (
        SimpleNamespace(
            maksimum_dusus_orani=0.12,
            guncel_dusus_orani=0.04,
        )
        if gunluk_var
        else None
    )
    baglam = (
        SimpleNamespace(
            analiz_kimligi="analiz123456",
            veri_kimligi="veri12345678",
            ayar_kimligi="ayar12345678",
        )
        if baglam_var
        else None
    )
    benchmark = (
        SimpleNamespace(
            al_tut=SimpleNamespace(
                net_getiri_orani=0.40,
            )
        )
        if benchmark_var
        else None
    )

    return SimpleNamespace(
        sembol="THYAO.IS",
        ilk_fiyat_tarihi="2021-01-01",
        son_fiyat_tarihi="2026-01-01",
        fiyat_bar_sayisi=1253,
        backtest_sonucu=backtest_sonucu,
        ozsermaye_raporu=ozsermaye,
        gunluk_ozsermaye_raporu=gunluk,
        analiz_baglami=baglam,
        hizalanmis_benchmark_karsilastirmasi=benchmark,
    )


def test_varsayilan_istek_ortak_profili_kullanir() -> None:
    istek = DashboardBacktestRequest()
    profil = istek.profil_olustur()

    assert istek.sembol == "THYAO.IS"
    assert profil.islem_gunu == 1253
    assert profil.indirme_donemi == "5y"
    assert profil.minimum_skor == 50
    assert profil.elde_tutma_gunu == 10


def test_sembol_bist_uzantisiyla_normalize_edilir() -> None:
    assert DashboardBacktestRequest(sembol=" tuprs ").sembol == "TUPRS.IS"
    assert DashboardBacktestRequest(sembol="ASELS.IS").sembol == "ASELS.IS"


def test_ozel_ayarlar_servis_yapilandirmasina_donusur() -> None:
    istek = DashboardBacktestRequest(
        sembol="ASELS",
        islem_gunu=500,
        indirme_donemi="2y",
        minimum_bar_sayisi=80,
        gorunum_secimi="pozitif",
        elde_tutma_gunu=7,
        minimum_skor=55,
        baslangic_sermayesi=250_000.0,
        pozisyon_yuzde=40.0,
        maliyet_yuzde=0.25,
        stop_yuzde=3.0,
        hedef_yuzde=8.0,
    )

    ayarlar = istek.servis_yapilandirmasi()

    assert ayarlar.islem_gunu == 500
    assert ayarlar.indirme_donemi == "2y"
    assert ayarlar.sinyal_ayarlari.minimum_bar_sayisi == 80
    assert ayarlar.backtest_ayarlari.minimum_skor == 55
    assert ayarlar.backtest_ayarlari.pozisyon_orani == pytest.approx(0.40)
    assert ayarlar.backtest_ayarlari.islem_maliyeti_orani == pytest.approx(0.0025)
    assert ayarlar.backtest_ayarlari.zarar_durdur_orani == pytest.approx(0.03)
    assert ayarlar.backtest_ayarlari.hedef_orani == pytest.approx(0.08)


def test_bos_sembol_reddedilir() -> None:
    with pytest.raises(ValueError, match="boş olamaz"):
        DashboardBacktestRequest(sembol="   ")


def test_gecersiz_minimum_skor_reddedilir() -> None:
    with pytest.raises(ValueError, match="Minimum skor"):
        DashboardBacktestRequest(minimum_skor=101)


def test_dashboard_servisi_istegi_backtest_servisine_iletir() -> None:
    sahte = SahteBacktestServisi(sahte_rapor())
    servis = BacktestDashboardService(sahte)
    istek = DashboardBacktestRequest(sembol="thyao")

    servis.calistir(istek)

    assert sahte.sembol == "THYAO.IS"
    assert sahte.yapilandirma is not None
    assert sahte.yapilandirma.backtest_ayarlari.minimum_skor == 50


def test_ozet_gunluk_risk_ve_kimlikleri_kullanir() -> None:
    sonuc = BacktestDashboardService(
        SahteBacktestServisi(sahte_rapor())
    ).calistir(DashboardBacktestRequest())

    ozet = sonuc.ozet

    assert ozet.fiyat_donemi == "2021-01-01 — 2026-01-01"
    assert ozet.analiz_kimligi == "analiz123456"
    assert ozet.veri_kimligi == "veri12345678"
    assert ozet.ayar_kimligi == "ayar12345678"
    assert ozet.toplam_getiri_yuzde == pytest.approx(25.0)
    assert ozet.maksimum_dusus_yuzde == pytest.approx(12.0)
    assert ozet.guncel_dusus_yuzde == pytest.approx(4.0)
    assert ozet.al_tut_getiri_yuzde == pytest.approx(40.0)


def test_gunluk_rapor_yoksa_tamamlanan_islem_dususu_kullanilir() -> None:
    sonuc = BacktestDashboardService(
        SahteBacktestServisi(
            sahte_rapor(
                gunluk_var=False,
                baglam_var=False,
                benchmark_var=False,
            )
        )
    ).calistir(DashboardBacktestRequest())

    assert sonuc.ozet.maksimum_dusus_yuzde == pytest.approx(18.0)
    assert sonuc.ozet.guncel_dusus_yuzde == 0.0
    assert sonuc.ozet.analiz_kimligi == "-"
    assert sonuc.ozet.al_tut_getiri_yuzde is None


def test_islemler_tablo_satirlarina_donusturulur() -> None:
    sonuc = BacktestDashboardService(
        SahteBacktestServisi(sahte_rapor())
    ).calistir(DashboardBacktestRequest())

    assert len(sonuc.islemler) == 1
    satir = sonuc.islemler[0]
    assert satir.sira == 1
    assert satir.sinyal_tarihi == "2026-01-02"
    assert satir.giris_tarihi == "2026-01-05"
    assert satir.cikis_tarihi == "2026-01-12"
    assert satir.net_getiri_yuzde == pytest.approx(9.78)
    assert satir.cikis_nedeni == "Hedef"


def test_islem_kaydi_turkce_tablo_basliklarini_kullanir() -> None:
    satir = DashboardTradeRow(
        sira=1,
        sinyal_tarihi="2026-01-02",
        giris_tarihi="2026-01-05",
        cikis_tarihi="2026-01-12",
        skor=72,
        giris_fiyati=100.0,
        cikis_fiyati=110.0,
        net_getiri_yuzde=9.78,
        elde_tutulan_bar=6,
        cikis_nedeni="Hedef",
    )

    kayit = satir.kayit()

    assert tuple(kayit) == (
        "No",
        "Sinyal",
        "Giriş",
        "Çıkış",
        "Skor",
        "Giriş Fiyatı",
        "Çıkış Fiyatı",
        "Net Getiri (%)",
        "Bar",
        "Çıkış Nedeni",
    )
    assert kayit["Net Getiri (%)"] == pytest.approx(9.78)
