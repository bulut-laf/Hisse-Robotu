from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backend.app.backtest.benchmark_comparison import (
    BenchmarkComparisonAnalyzer,
    BenchmarkComparisonError,
)


def fiyat_verisi_olustur() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [
                100.0,
                110.0,
                90.0,
                140.0,
            ],
            "High": [
                105.0,
                125.0,
                95.0,
                155.0,
            ],
            "Low": [
                95.0,
                105.0,
                85.0,
                135.0,
            ],
            "Close": [
                100.0,
                120.0,
                90.0,
                150.0,
            ],
            "Volume": [
                1_000_000.0,
                1_100_000.0,
                1_200_000.0,
                1_300_000.0,
            ],
        },
        index=pd.to_datetime(
            [
                "2025-01-01",
                "2025-06-01",
                "2025-09-01",
                "2026-01-01",
            ]
        ),
    )


def test_al_tut_getirisi_ve_sermayesi_hesaplanir() -> None:
    rapor = (
        BenchmarkComparisonAnalyzer()
        .analiz_et(
            fiyat_verisi=(
                fiyat_verisi_olustur()
            ),
            strateji_toplam_getiri_orani=0.80,
            strateji_maksimum_dusus_orani=0.20,
            baslangic_sermayesi=100_000.0,
            islem_maliyeti_orani=0.0,
        )
    )

    al_tut = rapor.al_tut

    assert al_tut.baslangic_tarihi == date(
        2025,
        1,
        1,
    )

    assert al_tut.bitis_tarihi == date(
        2026,
        1,
        1,
    )

    assert al_tut.takvim_gunu_sayisi == 365
    assert al_tut.giris_fiyati == 100.0
    assert al_tut.cikis_fiyati == 150.0

    assert (
        al_tut.brut_getiri_orani
        == pytest.approx(0.50)
    )

    assert (
        al_tut.net_getiri_orani
        == pytest.approx(0.50)
    )

    assert (
        al_tut.bitis_sermayesi
        == pytest.approx(150_000.0)
    )

    assert (
        al_tut.yilliklandirilmis_getiri_orani
        == pytest.approx(0.50)
    )


def test_al_tut_maksimum_dusus_ve_toparlanma_hesaplanir() -> None:
    rapor = (
        BenchmarkComparisonAnalyzer()
        .analiz_et(
            fiyat_verisi=(
                fiyat_verisi_olustur()
            ),
            strateji_toplam_getiri_orani=0.80,
            strateji_maksimum_dusus_orani=0.20,
            islem_maliyeti_orani=0.0,
        )
    )

    al_tut = rapor.al_tut

    assert (
        al_tut.maksimum_dusus_orani
        == pytest.approx(0.25)
    )

    assert (
        al_tut.maksimum_dusus_zirve_tarihi
        == date(
            2025,
            6,
            1,
        )
    )

    assert (
        al_tut.maksimum_dusus_dip_tarihi
        == date(
            2025,
            9,
            1,
        )
    )

    assert (
        al_tut.maksimum_dusus_toparlanma_tarihi
        == date(
            2026,
            1,
            1,
        )
    )

    assert al_tut.toparlandi_mi is True
    assert al_tut.guncel_dusus_orani == 0.0


def test_strateji_ve_al_tut_karsilastirilir() -> None:
    rapor = (
        BenchmarkComparisonAnalyzer()
        .analiz_et(
            fiyat_verisi=(
                fiyat_verisi_olustur()
            ),
            strateji_toplam_getiri_orani=0.80,
            strateji_maksimum_dusus_orani=0.20,
            islem_maliyeti_orani=0.0,
        )
    )

    sonuc = rapor.karsilastirma

    assert (
        sonuc.fazla_getiri_orani
        == pytest.approx(0.30)
    )

    assert (
        sonuc.strateji_yilliklandirilmis_getiri_orani
        == pytest.approx(0.80)
    )

    assert (
        sonuc.al_tut_yilliklandirilmis_getiri_orani
        == pytest.approx(0.50)
    )

    assert (
        sonuc.strateji_getiri_dusus_orani
        == pytest.approx(4.0)
    )

    assert (
        sonuc.al_tut_getiri_dusus_orani
        == pytest.approx(2.0)
    )

    assert sonuc.toplam_getiri_lideri == "Strateji"
    assert sonuc.risk_duzeltilmis_lider == "Strateji"


def test_islem_maliyetleri_al_tut_getirisine_uygulanir() -> None:
    rapor = (
        BenchmarkComparisonAnalyzer()
        .analiz_et(
            fiyat_verisi=(
                fiyat_verisi_olustur()
            ),
            strateji_toplam_getiri_orani=0.80,
            strateji_maksimum_dusus_orani=0.20,
            baslangic_sermayesi=100_000.0,
            islem_maliyeti_orani=0.001,
        )
    )

    beklenen_getiri = (
        (
            150.0
            * 0.999
        )
        / (
            100.0
            * 1.001
        )
        - 1.0
    )

    assert (
        rapor.al_tut.net_getiri_orani
        == pytest.approx(
            beklenen_getiri
        )
    )

    assert (
        rapor.al_tut.bitis_sermayesi
        == pytest.approx(
            100_000.0
            * (
                1.0
                + beklenen_getiri
            )
        )
    )


def test_tarih_araligi_ilk_uygun_veriyle_sinirlanir() -> None:
    rapor = (
        BenchmarkComparisonAnalyzer()
        .analiz_et(
            fiyat_verisi=(
                fiyat_verisi_olustur()
            ),
            strateji_toplam_getiri_orani=0.20,
            strateji_maksimum_dusus_orani=0.10,
            baslangic_tarihi=date(
                2025,
                2,
                1,
            ),
            bitis_tarihi=date(
                2025,
                12,
                1,
            ),
            islem_maliyeti_orani=0.0,
        )
    )

    assert (
        rapor.al_tut.baslangic_tarihi
        == date(
            2025,
            6,
            1,
        )
    )

    assert (
        rapor.al_tut.bitis_tarihi
        == date(
            2025,
            9,
            1,
        )
    )

    assert rapor.al_tut.giris_fiyati == 110.0
    assert rapor.al_tut.cikis_fiyati == 90.0


def test_gecersiz_veri_ve_ayarlar_hata_verir() -> None:
    analizci = BenchmarkComparisonAnalyzer()

    with pytest.raises(
        BenchmarkComparisonError,
        match="boş olamaz",
    ):
        analizci.analiz_et(
            fiyat_verisi=pd.DataFrame(),
            strateji_toplam_getiri_orani=0.10,
            strateji_maksimum_dusus_orani=0.10,
        )

    with pytest.raises(
        BenchmarkComparisonError,
        match="Eksik fiyat sütunları",
    ):
        analizci.analiz_et(
            fiyat_verisi=pd.DataFrame(
                {
                    "Close": [
                        100.0,
                        110.0,
                    ]
                },
                index=pd.date_range(
                    "2026-01-01",
                    periods=2,
                ),
            ),
            strateji_toplam_getiri_orani=0.10,
            strateji_maksimum_dusus_orani=0.10,
        )

    with pytest.raises(
        BenchmarkComparisonError,
        match="maksimum düşüşü",
    ):
        analizci.analiz_et(
            fiyat_verisi=(
                fiyat_verisi_olustur()
            ),
            strateji_toplam_getiri_orani=0.10,
            strateji_maksimum_dusus_orani=1.10,
        )

    with pytest.raises(
        BenchmarkComparisonError,
        match="Seçilen tarih aralığında",
    ):
        analizci.analiz_et(
            fiyat_verisi=(
                fiyat_verisi_olustur()
            ),
            strateji_toplam_getiri_orani=0.10,
            strateji_maksimum_dusus_orani=0.10,
            baslangic_tarihi=date(
                2030,
                1,
                1,
            ),
        )