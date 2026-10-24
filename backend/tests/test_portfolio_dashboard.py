from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from backend.app.ui.portfolio_dashboard import (
    PortfolioContributionRow,
    PortfolioDashboardError,
    PortfolioDashboardRequest,
    PortfolioDashboardResult,
    PortfolioDashboardService,
    PortfolioEquityRow,
    PreparedPortfolioSymbol,
    ozsermaye_eksen_araligi,
    sembolleri_hazirla,
)


class SahtePortfoyAnalizcisi:
    def __init__(self, rapor: object | None = None, hata: Exception | None = None) -> None:
        self.rapor = rapor
        self.hata = hata
        self.fiyat_verileri: dict[str, pd.DataFrame] | None = None
        self.islemler: tuple[object, ...] | None = None
        self.yapilandirma: object | None = None

    def analiz_et(
        self,
        fiyat_verileri: dict[str, pd.DataFrame],
        islemler: tuple[object, ...],
        yapilandirma: object | None = None,
    ) -> object:
        self.fiyat_verileri = fiyat_verileri
        self.islemler = islemler
        self.yapilandirma = yapilandirma
        if self.hata is not None:
            raise self.hata
        return self.rapor


def sahte_rapor() -> SimpleNamespace:
    katki = SimpleNamespace(
        sembol="THYAO.IS",
        islem_sayisi=12,
        kazanma_orani=0.625,
        toplam_ayrilan_sermaye=450_000.0,
        net_kar=25_000.0,
        baslangic_sermayesine_katki_orani=0.25,
    )
    gunluk_nokta = SimpleNamespace(
        tarih=date(2026, 1, 5),
        ozsermaye=125_000.0,
        dusus_orani=0.04,
        acik_pozisyon_sayisi=2,
        sermaye_kullanim_orani=0.75,
    )
    atlananlar = (
        SimpleNamespace(neden="Kapasite dolu."),
        SimpleNamespace(neden="Kapasite dolu."),
        SimpleNamespace(neden="Nakit yetersiz."),
    )
    return SimpleNamespace(
        ilk_tarih=date(2021, 10, 22),
        son_tarih=date(2026, 7, 21),
        tamamlanan_islem_sayisi=30,
        atlanan_islem_sayisi=3,
        bitis_sermayesi=180_000.0,
        toplam_getiri_orani=0.80,
        maksimum_dusus_orani=0.20,
        guncel_dusus_orani=0.05,
        kar_faktoru=1.75,
        maksimum_es_zamanli_pozisyon=3,
        ortalama_sermaye_kullanim_orani=0.55,
        maksimum_sermaye_kullanim_orani=1.0,
        sembol_katkilari=(katki,),
        gunluk_noktalar=(gunluk_nokta,),
        atlanan_islemler=atlananlar,
    )


def test_semboller_normalize_edilir_ve_tekrarlar_atilir() -> None:
    assert sembolleri_hazirla(" thyao, TUPRS; thyao\nASELS ") == (
        "THYAO.IS",
        "TUPRS.IS",
        "ASELS.IS",
    )


def test_portfoy_icin_en_az_iki_hisse_gerekir() -> None:
    with pytest.raises(ValueError, match="en az iki"):
        PortfolioDashboardRequest(semboller="THYAO")


def test_panel_en_fazla_on_hisseyi_kabul_eder() -> None:
    semboller = ",".join(f"HISSE{sira}" for sira in range(11))

    with pytest.raises(ValueError, match="en fazla 10"):
        PortfolioDashboardRequest(semboller=semboller)


def test_maksimum_pozisyon_hisse_sayisini_asamaz() -> None:
    with pytest.raises(ValueError, match="hisse sayısını aşamaz"):
        PortfolioDashboardRequest(
            semboller="THYAO,TUPRS",
            maksimum_es_zamanli_pozisyon=3,
        )


def test_istek_ortak_profili_ve_esit_slot_yapilandirmasini_kullanir() -> None:
    istek = PortfolioDashboardRequest(
        semboller="THYAO,TUPRS,ASELS",
        maksimum_es_zamanli_pozisyon=3,
        minimum_skor=55,
        baslangic_sermayesi=250_000.0,
        maliyet_yuzde=0.20,
        stop_yuzde=4.0,
    )

    profil = istek.profil_olustur()
    ayarlar = istek.portfoy_yapilandirmasi()

    assert profil.minimum_skor == 55
    assert profil.pozisyon_yuzde == 100.0
    assert ayarlar.baslangic_sermayesi == pytest.approx(250_000.0)
    assert ayarlar.pozisyon_basina_sermaye_orani == pytest.approx(1 / 3)
    assert ayarlar.islem_maliyeti_orani == pytest.approx(0.002)
    assert ayarlar.zarar_durdur_orani == pytest.approx(0.04)


def test_servis_tum_sembolleri_ayni_profil_ile_hazirlar() -> None:
    hazirlananlar: list[tuple[str, str]] = []

    def hazirlayici(sembol: str, profil: object) -> PreparedPortfolioSymbol:
        hazirlananlar.append((sembol, profil.ayar_kimligi))
        return PreparedPortfolioSymbol(
            sembol=sembol,
            fiyat_verisi=pd.DataFrame({"Close": [100.0]}),
            veri_kimligi=f"veri-{sembol}",
            islemler=(SimpleNamespace(sembol=sembol),),
        )

    analizci = SahtePortfoyAnalizcisi(sahte_rapor())
    istek = PortfolioDashboardRequest(
        semboller="THYAO,TUPRS,ASELS",
        maksimum_es_zamanli_pozisyon=2,
    )

    PortfolioDashboardService(hazirlayici, analizci).calistir(istek)

    assert [kayit[0] for kayit in hazirlananlar] == [
        "THYAO.IS",
        "TUPRS.IS",
        "ASELS.IS",
    ]
    assert len({kayit[1] for kayit in hazirlananlar}) == 1
    assert set(analizci.fiyat_verileri or {}) == {
        "THYAO.IS",
        "TUPRS.IS",
        "ASELS.IS",
    }
    assert len(analizci.islemler or ()) == 3
    assert analizci.yapilandirma.maksimum_es_zamanli_pozisyon == 2


def test_servis_portfoy_ozetini_yuzdelere_donusturur() -> None:
    def hazirlayici(sembol: str, profil: object) -> PreparedPortfolioSymbol:
        return PreparedPortfolioSymbol(
            sembol=sembol,
            fiyat_verisi=pd.DataFrame({"Close": [100.0]}),
            veri_kimligi=f"kimlik-{sembol}",
            islemler=(),
        )

    sonuc = PortfolioDashboardService(
        hazirlayici,
        SahtePortfoyAnalizcisi(sahte_rapor()),
    ).calistir(
        PortfolioDashboardRequest(
            semboller="THYAO,TUPRS",
            maksimum_es_zamanli_pozisyon=2,
        )
    )

    ozet = sonuc.ozet
    assert ozet.portfoy_donemi == "2021-10-22 — 2026-07-21"
    assert ozet.tamamlanan_islem_sayisi == 30
    assert ozet.atlanan_islem_sayisi == 3
    assert ozet.toplam_getiri_yuzde == pytest.approx(80.0)
    assert ozet.maksimum_dusus_yuzde == pytest.approx(20.0)
    assert ozet.guncel_dusus_yuzde == pytest.approx(5.0)
    assert ozet.ortalama_sermaye_kullanim_yuzde == pytest.approx(55.0)
    assert len(ozet.portfoy_veri_kimligi) == 12


def test_hisse_katkisi_turkce_tablo_kaydina_donusur() -> None:
    satir = PortfolioContributionRow(
        sembol="ASELS.IS",
        islem_sayisi=10,
        kazanma_yuzde=60.0,
        toplam_ayrilan_sermaye=500_000.0,
        net_kar=50_000.0,
        baslangica_katki_yuzde=50.0,
    )

    kayit = satir.kayit()

    assert tuple(kayit) == (
        "Sembol",
        "İşlem",
        "Kazanma (%)",
        "Toplam Ayrılan Sermaye",
        "Net Kâr",
        "Başlangıca Katkı (%)",
    )
    assert kayit["Net Kâr"] == pytest.approx(50_000.0)


def test_gunluk_ozsermaye_grafik_kaydina_donusur() -> None:
    satir = PortfolioEquityRow(
        tarih="2026-01-05",
        ozsermaye=125_000.0,
        dusus_yuzde=4.0,
        acik_pozisyon_sayisi=2,
        sermaye_kullanim_yuzde=75.0,
    )

    assert satir.kayit() == {
        "Tarih": "2026-01-05",
        "Özsermaye": 125_000.0,
        "Düşüş (%)": 4.0,
        "Açık Pozisyon": 2,
        "Sermaye Kullanımı (%)": 75.0,
    }


def test_atlanan_islem_nedenleri_sayilarak_siralanir() -> None:
    def hazirlayici(sembol: str, profil: object) -> PreparedPortfolioSymbol:
        return PreparedPortfolioSymbol(
            sembol=sembol,
            fiyat_verisi=pd.DataFrame({"Close": [100.0]}),
            veri_kimligi=sembol,
            islemler=(),
        )

    sonuc = PortfolioDashboardService(
        hazirlayici,
        SahtePortfoyAnalizcisi(sahte_rapor()),
    ).calistir(
        PortfolioDashboardRequest(
            semboller="THYAO,TUPRS",
            maksimum_es_zamanli_pozisyon=2,
        )
    )

    assert sonuc.atlanma_kayitlari() == [
        {"Neden": "Kapasite dolu.", "Adet": 2},
        {"Neden": "Nakit yetersiz.", "Adet": 1},
    ]


def test_gecersiz_istek_tipi_reddedilir() -> None:
    with pytest.raises(TypeError, match="PortfolioDashboardRequest"):
        PortfolioDashboardService().calistir(object())


def test_sembol_hazirlama_hatasi_sembol_bilgisiyle_sarilir() -> None:
    def hatali_hazirlayici(sembol: str, profil: object) -> PreparedPortfolioSymbol:
        raise ValueError("veri bozuk")

    with pytest.raises(
        PortfolioDashboardError,
        match="THYAO.IS hazırlanamadı: veri bozuk",
    ):
        PortfolioDashboardService(
            hatali_hazirlayici,
            SahtePortfoyAnalizcisi(sahte_rapor()),
        ).calistir(
            PortfolioDashboardRequest(
                semboller="THYAO,TUPRS",
                maksimum_es_zamanli_pozisyon=2,
            )
        )


def test_portfoy_motoru_hatasi_kullanici_mesajina_donusur() -> None:
    def hazirlayici(sembol: str, profil: object) -> PreparedPortfolioSymbol:
        return PreparedPortfolioSymbol(
            sembol=sembol,
            fiyat_verisi=pd.DataFrame({"Close": [100.0]}),
            veri_kimligi=sembol,
            islemler=(),
        )

    with pytest.raises(
        PortfolioDashboardError,
        match="Portföy backtest’i tamamlanamadı",
    ):
        PortfolioDashboardService(
            hazirlayici,
            SahtePortfoyAnalizcisi(hata=ValueError("hesaplama hatası")),
        ).calistir(
            PortfolioDashboardRequest(
                semboller="THYAO,TUPRS",
                maksimum_es_zamanli_pozisyon=2,
            )
        )


def test_hisse_katkisi_kompakt_kayda_donusur() -> None:
    satir = PortfolioContributionRow(
        sembol="ASELS.IS",
        islem_sayisi=10,
        kazanma_yuzde=60.0,
        toplam_ayrilan_sermaye=500_000.0,
        net_kar=50_000.0,
        baslangica_katki_yuzde=50.0,
    )

    assert satir.kompakt_kayit() == {
        "Sembol": "ASELS.IS",
        "İşlem": 10,
        "Kazanma (%)": 60.0,
        "Net Kâr": 50_000.0,
        "Katkı (%)": 50.0,
    }


def test_hisse_katkisi_hacim_kaydina_ayrilir() -> None:
    satir = PortfolioContributionRow(
        sembol="TUPRS.IS",
        islem_sayisi=8,
        kazanma_yuzde=50.0,
        toplam_ayrilan_sermaye=750_000.0,
        net_kar=40_000.0,
        baslangica_katki_yuzde=40.0,
    )

    assert satir.hacim_kaydi() == {
        "Sembol": "TUPRS.IS",
        "Toplam Ayrılan Sermaye": 750_000.0,
    }


def test_sonuc_kompakt_katki_ve_hacim_kayitlarini_ayirir() -> None:
    satir = PortfolioContributionRow(
        sembol="THYAO.IS",
        islem_sayisi=12,
        kazanma_yuzde=54.0,
        toplam_ayrilan_sermaye=900_000.0,
        net_kar=90_000.0,
        baslangica_katki_yuzde=90.0,
    )
    sonuc = PortfolioDashboardResult(
        ozet=SimpleNamespace(),
        katkilar=(satir,),
        gunluk_ozsermaye=(),
        atlanma_nedenleri=(),
    )

    assert tuple(sonuc.kompakt_katki_kayitlari()[0]) == (
        "Sembol",
        "İşlem",
        "Kazanma (%)",
        "Net Kâr",
        "Katkı (%)",
    )
    assert sonuc.hacim_kayitlari() == [
        {
            "Sembol": "THYAO.IS",
            "Toplam Ayrılan Sermaye": 900_000.0,
        }
    ]


def test_ozsermaye_eksen_araligi_negatif_bosluk_uretmez() -> None:
    aralik = ozsermaye_eksen_araligi(
        [
            {"Özsermaye": 100_000.0},
            {"Özsermaye": 700_000.0},
        ]
    )

    assert aralik == pytest.approx((70_000.0, 730_000.0))
    assert aralik[0] >= 0.0


def test_ozsermaye_eksen_araligi_tek_noktayi_cevreler() -> None:
    assert ozsermaye_eksen_araligi(
        [{"Özsermaye": 100_000.0}]
    ) == pytest.approx((95_000.0, 105_000.0))


def test_ozsermaye_eksen_araligi_bos_kayitta_yoktur() -> None:
    assert ozsermaye_eksen_araligi([]) is None

