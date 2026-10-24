from __future__ import annotations

from datetime import date

import pytest

from backend.app.backtest.backtest_models import (
    BacktestTrade,
)
from backend.app.backtest.performance_breakdown import (
    PerformanceBreakdownAnalyzer,
    PerformanceBreakdownError,
)


GORUNUM = "Pozitif Teknik Görünüm"


def islem_olustur(
    sembol: str,
    sinyal_tarihi: date,
    giris_tarihi: date,
    cikis_tarihi: date,
    giris_fiyati: float,
    cikis_fiyati: float,
    cikis_nedeni: str,
) -> BacktestTrade:
    return BacktestTrade.olustur(
        sembol=sembol,
        sinyal_tarihi=sinyal_tarihi,
        giris_tarihi=giris_tarihi,
        cikis_tarihi=cikis_tarihi,
        giris_fiyati=giris_fiyati,
        cikis_fiyati=cikis_fiyati,
        skor=70,
        teknik_gorunum=GORUNUM,
        elde_tutulan_bar=5,
        cikis_nedeni=cikis_nedeni,
        islem_maliyeti_orani=0.0,
    )


def ornek_islemler() -> tuple[
    BacktestTrade,
    ...,
]:
    return (
        islem_olustur(
            sembol="AAA.IS",
            sinyal_tarihi=date(2025, 2, 2),
            giris_tarihi=date(2025, 2, 3),
            cikis_tarihi=date(2025, 2, 10),
            giris_fiyati=100.0,
            cikis_fiyati=120.0,
            cikis_nedeni="Hedef",
        ),
        islem_olustur(
            sembol="AAA.IS",
            sinyal_tarihi=date(2024, 2, 2),
            giris_tarihi=date(2024, 2, 3),
            cikis_tarihi=date(2024, 2, 10),
            giris_fiyati=100.0,
            cikis_fiyati=95.0,
            cikis_nedeni="Zarar Durdur",
        ),
        islem_olustur(
            sembol="AAA.IS",
            sinyal_tarihi=date(2024, 1, 2),
            giris_tarihi=date(2024, 1, 3),
            cikis_tarihi=date(2024, 1, 10),
            giris_fiyati=100.0,
            cikis_fiyati=110.0,
            cikis_nedeni="Hedef",
        ),
        islem_olustur(
            sembol="AAA.IS",
            sinyal_tarihi=date(2025, 1, 2),
            giris_tarihi=date(2025, 1, 3),
            cikis_tarihi=date(2025, 1, 10),
            giris_fiyati=100.0,
            cikis_fiyati=110.0,
            cikis_nedeni="Süre Sonu",
        ),
    )


def test_yillik_performans_ve_sermaye_aktarimi_hesaplanir() -> None:
    rapor = (
        PerformanceBreakdownAnalyzer()
        .analiz_et(
            islemler=ornek_islemler(),
            baslangic_sermayesi=100_000.0,
            pozisyon_orani=1.0,
        )
    )

    assert rapor.yil_sayisi == 2

    yil_2024 = (
        rapor.yillik_performanslar[0]
    )

    yil_2025 = (
        rapor.yillik_performanslar[1]
    )

    assert yil_2024.yil == 2024
    assert yil_2024.islem_sayisi == 2
    assert yil_2024.kazanan_islem_sayisi == 1
    assert yil_2024.kaybeden_islem_sayisi == 1

    assert (
        yil_2024.kazanma_orani
        == pytest.approx(0.50)
    )

    assert (
        yil_2024.ortalama_net_getiri_orani
        == pytest.approx(0.025)
    )

    assert (
        yil_2024.bilesik_getiri_orani
        == pytest.approx(0.045)
    )

    assert (
        yil_2024.kar_faktoru
        == pytest.approx(2.0)
    )

    assert (
        yil_2024.yil_basi_sermayesi
        == pytest.approx(100_000.0)
    )

    assert (
        yil_2024.yil_sonu_sermayesi
        == pytest.approx(104_500.0)
    )

    assert yil_2025.yil == 2025
    assert yil_2025.islem_sayisi == 2
    assert yil_2025.kazanan_islem_sayisi == 2
    assert yil_2025.kaybeden_islem_sayisi == 0
    assert yil_2025.kazanma_orani == 1.0

    assert (
        yil_2025.ortalama_net_getiri_orani
        == pytest.approx(0.15)
    )

    assert (
        yil_2025.bilesik_getiri_orani
        == pytest.approx(0.32)
    )

    assert yil_2025.kar_faktoru is None

    assert (
        yil_2025.yil_basi_sermayesi
        == pytest.approx(104_500.0)
    )

    assert (
        yil_2025.yil_sonu_sermayesi
        == pytest.approx(137_940.0)
    )

    assert (
        rapor.bitis_sermayesi
        == pytest.approx(137_940.0)
    )

    assert (
        rapor.toplam_bilesik_getiri_orani
        == pytest.approx(0.3794)
    )


def test_cikis_nedeni_dagilimlari_hesaplanir() -> None:
    rapor = (
        PerformanceBreakdownAnalyzer()
        .analiz_et(
            islemler=ornek_islemler()
        )
    )

    performanslar = {
        performans.cikis_nedeni: performans
        for performans
        in rapor.cikis_nedeni_performanslari
    }

    hedef = performanslar["Hedef"]
    zarar_durdur = performanslar[
        "Zarar Durdur"
    ]
    sure_sonu = performanslar[
        "Süre Sonu"
    ]

    assert hedef.islem_sayisi == 2

    assert (
        hedef.toplam_islem_orani
        == pytest.approx(0.50)
    )

    assert hedef.kazanan_islem_sayisi == 2
    assert hedef.kazanma_orani == 1.0

    assert (
        hedef.ortalama_net_getiri_orani
        == pytest.approx(0.15)
    )

    assert (
        hedef.bilesik_getiri_orani
        == pytest.approx(0.32)
    )

    assert zarar_durdur.islem_sayisi == 1
    assert zarar_durdur.kaybeden_islem_sayisi == 1

    assert (
        zarar_durdur.ortalama_net_getiri_orani
        == pytest.approx(-0.05)
    )

    assert sure_sonu.islem_sayisi == 1
    assert sure_sonu.kazanan_islem_sayisi == 1


def test_en_karli_ve_en_zararli_yil_bulunur() -> None:
    rapor = (
        PerformanceBreakdownAnalyzer()
        .analiz_et(
            islemler=ornek_islemler()
        )
    )

    assert rapor.en_karli_yil is not None
    assert rapor.en_zararli_yil is not None

    assert rapor.en_karli_yil.yil == 2025
    assert rapor.en_zararli_yil.yil == 2024


def test_pozisyon_orani_bilesik_sermayeye_uygulanir() -> None:
    rapor = (
        PerformanceBreakdownAnalyzer()
        .analiz_et(
            islemler=(
                ornek_islemler()[1],
                ornek_islemler()[2],
            ),
            baslangic_sermayesi=100_000.0,
            pozisyon_orani=0.50,
        )
    )

    assert (
        rapor.toplam_bilesik_getiri_orani
        == pytest.approx(0.02375)
    )

    assert (
        rapor.bitis_sermayesi
        == pytest.approx(102_375.0)
    )


def test_bos_islem_listesi_bos_rapor_dondurur() -> None:
    rapor = (
        PerformanceBreakdownAnalyzer()
        .analiz_et(
            islemler=(),
            baslangic_sermayesi=100_000.0,
        )
    )

    assert rapor.yil_sayisi == 0
    assert rapor.yillik_performanslar == ()
    assert rapor.cikis_nedeni_performanslari == ()
    assert rapor.en_karli_yil is None
    assert rapor.en_zararli_yil is None
    assert rapor.bitis_sermayesi == 100_000.0
    assert rapor.toplam_bilesik_getiri_orani == 0.0


def test_gecersiz_ayarlar_hata_verir() -> None:
    analizci = PerformanceBreakdownAnalyzer()

    with pytest.raises(
        PerformanceBreakdownError,
        match="Başlangıç sermayesi",
    ):
        analizci.analiz_et(
            islemler=(),
            baslangic_sermayesi=0.0,
        )

    with pytest.raises(
        PerformanceBreakdownError,
        match="Pozisyon oranı",
    ):
        analizci.analiz_et(
            islemler=(),
            pozisyon_orani=0.0,
        )

    with pytest.raises(
        PerformanceBreakdownError,
        match="Pozisyon oranı",
    ):
        analizci.analiz_et(
            islemler=(),
            pozisyon_orani=1.10,
        )