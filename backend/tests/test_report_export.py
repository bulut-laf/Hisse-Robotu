from __future__ import annotations

from dataclasses import replace

import pytest

from backend.app.ui.backtest_dashboard import (
    DashboardResult,
    DashboardSummary,
    DashboardTradeRow,
)
from backend.app.ui.portfolio_dashboard import (
    PortfolioContributionRow,
    PortfolioDashboardResult,
    PortfolioDashboardSummary,
    PortfolioEquityRow,
    PortfolioSkippedReasonRow,
)
from backend.app.ui.report_export import (
    UTF8_BOM,
    csv_baytlari,
    dengeli_sayfa_boyutlari,
    guvenli_dosya_parcasi,
    portfoy_dosya_adlari,
    portfoy_katki_csv_baytlari,
    portfoy_ozsermaye_csv_baytlari,
    portfoy_pdf_baytlari,
    tek_hisse_dosya_adlari,
    tek_hisse_islem_csv_baytlari,
    tek_hisse_pdf_baytlari,
)


def tek_hisse_sonucu(*, islem_var: bool = True) -> DashboardResult:
    ozet = DashboardSummary(
        sembol="THYAO.IS",
        fiyat_donemi="2021-07-28 — 2026-07-24",
        fiyat_bar_sayisi=1253,
        analiz_kimligi="bca78e27e797",
        veri_kimligi="d2cf3f3e9fe0",
        ayar_kimligi="6ed651a92e8c",
        tamamlanan_islem_sayisi=1 if islem_var else 0,
        atlanan_sinyal_sayisi=5,
        kazanma_yuzde=54.39,
        toplam_getiri_yuzde=425.63,
        bitis_sermayesi=525_633.62,
        maksimum_dusus_yuzde=46.97,
        guncel_dusus_yuzde=40.02,
        kar_faktoru=1.77,
        al_tut_getiri_yuzde=2215.23,
    )
    islemler = (
        DashboardTradeRow(
            sira=1,
            sinyal_tarihi="2021-10-21",
            giris_tarihi="2021-10-22",
            cikis_tarihi="2021-11-02",
            skor=54,
            giris_fiyati=13.69,
            cikis_fiyati=15.05,
            net_getiri_yuzde=9.78,
            elde_tutulan_bar=7,
            cikis_nedeni="Hedef",
        ),
    ) if islem_var else ()
    return DashboardResult(ozet=ozet, islemler=islemler)


def cok_islemli_tek_hisse_sonucu(adet: int) -> DashboardResult:
    temel = tek_hisse_sonucu()
    ozet = replace(
        temel.ozet,
        tamamlanan_islem_sayisi=adet,
    )
    islemler = tuple(
        DashboardTradeRow(
            sira=sira,
            sinyal_tarihi="2025-01-02",
            giris_tarihi="2025-01-03",
            cikis_tarihi="2025-01-10",
            skor=50 + (sira % 20),
            giris_fiyati=100.0 + sira,
            cikis_fiyati=105.0 + sira,
            net_getiri_yuzde=4.78,
            elde_tutulan_bar=5,
            cikis_nedeni="Süre Sonu",
        )
        for sira in range(1, adet + 1)
    )
    return DashboardResult(ozet=ozet, islemler=islemler)


def portfoy_sonucu(
    *,
    ozsermaye_var: bool = True,
    atlanma_var: bool = True,
) -> PortfolioDashboardResult:
    ozet = PortfolioDashboardSummary(
        semboller=("THYAO.IS", "TUPRS.IS", "ASELS.IS"),
        portfoy_donemi="2021-10-21 — 2026-07-24",
        ayar_kimligi="6ed651a92e8c",
        portfoy_veri_kimligi="5a449547fa8e",
        tamamlanan_islem_sayisi=349,
        atlanan_islem_sayisi=0 if not atlanma_var else 2,
        bitis_sermayesi=640_959.93,
        toplam_getiri_yuzde=540.96,
        maksimum_dusus_yuzde=27.08,
        guncel_dusus_yuzde=3.48,
        kar_faktoru=1.57,
        gerceklesen_maksimum_pozisyon=3,
        ortalama_sermaye_kullanim_yuzde=51.59,
        maksimum_sermaye_kullanim_yuzde=100.0,
    )
    katkilar = (
        PortfolioContributionRow(
            sembol="ASELS.IS",
            islem_sayisi=126,
            kazanma_yuzde=52.38,
            toplam_ayrilan_sermaye=15_544_865.13,
            net_kar=290_187.75,
            baslangica_katki_yuzde=290.19,
        ),
    )
    gunluk = (
        PortfolioEquityRow(
            tarih="2021-10-22",
            ozsermaye=100_000.0,
            dusus_yuzde=0.0,
            acik_pozisyon_sayisi=1,
            sermaye_kullanim_yuzde=33.33,
        ),
        PortfolioEquityRow(
            tarih="2026-07-21",
            ozsermaye=640_959.93,
            dusus_yuzde=3.48,
            acik_pozisyon_sayisi=0,
            sermaye_kullanim_yuzde=0.0,
        ),
    ) if ozsermaye_var else ()
    atlanmalar = (
        PortfolioSkippedReasonRow(neden="Kapasite dolu.", adet=2),
    ) if atlanma_var else ()
    return PortfolioDashboardResult(
        ozet=ozet,
        katkilar=katkilar,
        gunluk_ozsermaye=gunluk,
        atlanma_nedenleri=atlanmalar,
    )


def test_guvenli_dosya_parcasi_turkce_ve_ozel_karakterleri_temizler() -> None:
    assert guvenli_dosya_parcasi("Çoklu Hisse / ŞĞİ") == "Coklu_Hisse_SGI"
    assert guvenli_dosya_parcasi("   ") == "rapor"


def test_tek_hisse_dosya_adlari_kimlik_icerir() -> None:
    adlar = tek_hisse_dosya_adlari(tek_hisse_sonucu())

    assert adlar.csv == "THYAO_IS_backtest_bca78e27e797_islemler.csv"
    assert adlar.pdf == "THYAO_IS_backtest_bca78e27e797_rapor.pdf"


def test_portfoy_dosya_adlari_sembol_ve_veri_kimligi_icerir() -> None:
    adlar = portfoy_dosya_adlari(portfoy_sonucu())

    assert adlar.contribution_csv.endswith("_katki.csv")
    assert adlar.equity_csv.endswith("_gunluk_ozsermaye.csv")
    assert "THYAO_IS_TUPRS_IS_ASELS_IS" in adlar.pdf
    assert "5a449547fa8e" in adlar.pdf


def test_csv_baytlari_utf8_bom_ve_noktali_virgul_kullanir() -> None:
    veri = csv_baytlari(("Sembol", "Net Kâr"), ({"Sembol": "ŞİRKET", "Net Kâr": 12.5},))

    assert veri.startswith(UTF8_BOM)
    metin = veri[len(UTF8_BOM):].decode("utf-8")
    assert metin.splitlines() == ["Sembol;Net Kâr", "ŞİRKET;12.5"]


def test_tek_hisse_csv_islem_basliklarini_ve_degerlerini_icerir() -> None:
    veri = tek_hisse_islem_csv_baytlari(tek_hisse_sonucu())
    metin = veri[len(UTF8_BOM):].decode("utf-8")

    assert "No;Sinyal;Giriş;Çıkış;Skor" in metin
    assert "2021-10-21;2021-10-22;2021-11-02;54" in metin
    assert metin.rstrip().endswith("7;Hedef")


def test_tek_hisse_csv_islem_yokken_yalnizca_baslik_uretir() -> None:
    veri = tek_hisse_islem_csv_baytlari(tek_hisse_sonucu(islem_var=False))
    satirlar = veri[len(UTF8_BOM):].decode("utf-8").splitlines()

    assert len(satirlar) == 1
    assert satirlar[0].startswith("No;Sinyal;Giriş")


def test_portfoy_katki_csv_tum_katki_alanlarini_icerir() -> None:
    veri = portfoy_katki_csv_baytlari(portfoy_sonucu())
    metin = veri[len(UTF8_BOM):].decode("utf-8")

    assert "Toplam Ayrılan Sermaye" in metin
    assert "ASELS.IS;126;52.38;15544865.13;290187.75;290.19" in metin


def test_portfoy_ozsermaye_csv_gunluk_risk_alanlarini_icerir() -> None:
    veri = portfoy_ozsermaye_csv_baytlari(portfoy_sonucu())
    metin = veri[len(UTF8_BOM):].decode("utf-8")

    assert "Tarih;Özsermaye;Düşüş (%);Açık Pozisyon;Sermaye Kullanımı (%)" in metin
    assert "2026-07-21;640959.93;3.48;0;0" in metin


def test_tek_hisse_pdf_gecerli_pdf_baytlari_uretir() -> None:
    veri = tek_hisse_pdf_baytlari(tek_hisse_sonucu())

    assert veri.startswith(b"%PDF-")
    assert b"%%EOF" in veri[-64:]
    assert len(veri) > 10_000


def test_portfoy_pdf_gecerli_pdf_baytlari_uretir() -> None:
    veri = portfoy_pdf_baytlari(portfoy_sonucu())

    assert veri.startswith(b"%PDF-")
    assert b"%%EOF" in veri[-64:]
    assert len(veri) > 10_000


def test_tek_hisse_pdf_islem_olmadan_da_uretilir() -> None:
    veri = tek_hisse_pdf_baytlari(tek_hisse_sonucu(islem_var=False))

    assert veri.startswith(b"%PDF-")
    assert len(veri) > 8_000


def test_portfoy_pdf_ozsermaye_ve_atlanma_olmadan_da_uretilir() -> None:
    veri = portfoy_pdf_baytlari(
        portfoy_sonucu(ozsermaye_var=False, atlanma_var=False)
    )

    assert veri.startswith(b"%PDF-")
    assert len(veri) > 8_000


def test_dengeli_sayfa_boyutlari_bos_kayit_icin_bos_sonuc_verir() -> None:
    assert dengeli_sayfa_boyutlari(0) == ()


def test_dengeli_sayfa_boyutlari_tek_sayfayi_korur() -> None:
    assert dengeli_sayfa_boyutlari(24, maksimum_satir=24) == (24,)


def test_dengeli_sayfa_boyutlari_son_sayfayi_kucuk_birakmaz() -> None:
    assert dengeli_sayfa_boyutlari(25, maksimum_satir=24) == (13, 12)
    assert dengeli_sayfa_boyutlari(114, maksimum_satir=24) == (23, 23, 23, 23, 22)


def test_dengeli_sayfa_boyutlari_gecersiz_degerleri_reddeder() -> None:
    with pytest.raises(ValueError, match="negatif"):
        dengeli_sayfa_boyutlari(-1)
    with pytest.raises(ValueError, match="pozitif"):
        dengeli_sayfa_boyutlari(10, maksimum_satir=0)


def test_tek_hisse_pdf_114_islemi_dengeli_bes_ayrinti_sayfasina_boler() -> None:
    veri = tek_hisse_pdf_baytlari(cok_islemli_tek_hisse_sonucu(114))

    sayfa_sayisi = veri.count(b"/Type /Page") - veri.count(b"/Type /Pages")
    assert sayfa_sayisi == 6
    assert len(veri) > 25_000


def test_portfoy_pdf_kompakt_ozetle_tek_sayfaya_sigar() -> None:
    veri = portfoy_pdf_baytlari(portfoy_sonucu(atlanma_var=False))

    sayfa_sayisi = veri.count(b"/Type /Page") - veri.count(b"/Type /Pages")
    assert sayfa_sayisi == 1
