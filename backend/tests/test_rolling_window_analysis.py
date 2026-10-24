from __future__ import annotations

import pandas as pd
import pytest

from backend.app.backtest.backtest_models import (
    BacktestConfig,
    BacktestSignal,
)
from backend.app.backtest.rolling_window_analysis import (
    RollingWindowAnalysisError,
    RollingWindowAnalyzer,
    RollingWindowConfig,
)


GORUNUM = "Pozitif Teknik Görünüm"


def fiyat_verisi_olustur(
    bar_sayisi: int,
    ozel_kapanislar: dict[int, float] | None = None,
) -> pd.DataFrame:
    ozel_kapanislar = ozel_kapanislar or {}
    acilislar = [100.0 for _ in range(bar_sayisi)]
    kapanislar = [
        ozel_kapanislar.get(konum, 100.0)
        for konum in range(bar_sayisi)
    ]

    return pd.DataFrame(
        {
            "Open": acilislar,
            "High": [
                max(acilis, kapanis) + 1.0
                for acilis, kapanis in zip(
                    acilislar,
                    kapanislar,
                )
            ],
            "Low": [
                min(acilis, kapanis) - 1.0
                for acilis, kapanis in zip(
                    acilislar,
                    kapanislar,
                )
            ],
            "Close": kapanislar,
            "Volume": [
                1_000_000.0
                for _ in range(bar_sayisi)
            ],
        },
        index=pd.date_range(
            "2026-01-01",
            periods=bar_sayisi,
            freq="D",
        ),
    )


def sinyal_olustur(
    fiyat_verisi: pd.DataFrame,
    konum: int,
    sembol: str = "AAA.IS",
    skor: int = 60,
) -> BacktestSignal:
    return BacktestSignal(
        sembol=sembol,
        sinyal_tarihi=fiyat_verisi.index[konum].date(),
        skor=skor,
        teknik_gorunum=GORUNUM,
    )


def baz_ayar(
    elde_tutma_gunu: int = 1,
    minimum_skor: int = 50,
) -> BacktestConfig:
    return BacktestConfig(
        elde_tutma_gunu=elde_tutma_gunu,
        minimum_skor=minimum_skor,
        baslangic_sermayesi=100_000.0,
        pozisyon_orani=1.0,
        islem_maliyeti_orani=0.0,
        zarar_durdur_orani=None,
        hedef_orani=None,
    )


def test_pencere_yapilandirmasi_gecersiz_degerleri_reddeder() -> None:
    with pytest.raises(ValueError, match="en az 2"):
        RollingWindowConfig(pencere_bar_sayisi=1)

    with pytest.raises(ValueError, match="Adım bar"):
        RollingWindowConfig(adim_bar_sayisi=0)

    with pytest.raises(ValueError, match="büyük olamaz"):
        RollingWindowConfig(
            pencere_bar_sayisi=10,
            adim_bar_sayisi=11,
        )

    with pytest.raises(ValueError, match="Minimum işlem"):
        RollingWindowConfig(minimum_islem_sayisi=0)


def test_kayan_pencereler_son_fiyat_barini_kapsar() -> None:
    fiyatlar = fiyat_verisi_olustur(23)
    rapor = RollingWindowAnalyzer().analiz_et(
        sembol="AAA",
        fiyat_verisi=fiyatlar,
        sinyaller=(),
        backtest_yapilandirmasi=baz_ayar(),
        yapilandirma=RollingWindowConfig(
            pencere_bar_sayisi=10,
            adim_bar_sayisi=6,
            minimum_islem_sayisi=1,
        ),
    )

    assert rapor.pencere_sayisi == 4
    assert [
        pencere.baslangic_tarihi
        for pencere in rapor.pencereler
    ] == [
        fiyatlar.index[konum].date()
        for konum in (0, 6, 12, 13)
    ]
    assert rapor.pencereler[-1].bitis_tarihi == (
        fiyatlar.index[-1].date()
    )
    assert all(
        pencere.bar_sayisi == 10
        for pencere in rapor.pencereler
    )


def test_pencere_metrikleri_ve_saglamlik_ozeti_hesaplanir() -> None:
    fiyatlar = fiyat_verisi_olustur(
        18,
        ozel_kapanislar={
            1: 110.0,
            7: 90.0,
            13: 120.0,
        },
    )
    sinyaller = tuple(
        sinyal_olustur(fiyatlar, konum)
        for konum in (0, 6, 12)
    )
    rapor = RollingWindowAnalyzer().analiz_et(
        sembol="AAA.IS",
        fiyat_verisi=fiyatlar,
        sinyaller=sinyaller,
        backtest_yapilandirmasi=baz_ayar(),
        yapilandirma=RollingWindowConfig(
            pencere_bar_sayisi=6,
            adim_bar_sayisi=6,
            minimum_islem_sayisi=1,
        ),
    )

    assert rapor.degerlendirilen_pencere_sayisi == 3
    assert rapor.pozitif_pencere_sayisi == 2
    assert rapor.pozitif_pencere_orani == pytest.approx(2 / 3)
    assert rapor.medyan_toplam_getiri_orani == pytest.approx(0.10)
    assert rapor.minimum_toplam_getiri_orani == pytest.approx(-0.10)
    assert rapor.maksimum_toplam_getiri_orani == pytest.approx(0.20)
    assert rapor.en_iyi_pencere is not None
    assert rapor.en_iyi_pencere.sira == 3
    assert rapor.en_zayif_pencere is not None
    assert rapor.en_zayif_pencere.sira == 2
    assert rapor.pencereler[1].maksimum_dusus_orani == pytest.approx(
        0.10
    )


def test_minimum_islem_esiginin_altindaki_pencereler_ozete_alinmaz() -> None:
    fiyatlar = fiyat_verisi_olustur(
        18,
        ozel_kapanislar={1: 110.0, 7: 90.0, 13: 120.0},
    )
    rapor = RollingWindowAnalyzer().analiz_et(
        sembol="AAA.IS",
        fiyat_verisi=fiyatlar,
        sinyaller=tuple(
            sinyal_olustur(fiyatlar, konum)
            for konum in (0, 6, 12)
        ),
        backtest_yapilandirmasi=baz_ayar(),
        yapilandirma=RollingWindowConfig(
            pencere_bar_sayisi=6,
            adim_bar_sayisi=6,
            minimum_islem_sayisi=2,
        ),
    )

    assert rapor.pencere_sayisi == 3
    assert rapor.degerlendirilen_pencere_sayisi == 0
    assert rapor.yetersiz_pencere_sayisi == 3
    assert rapor.medyan_toplam_getiri_orani is None
    assert rapor.en_iyi_pencere is None
    assert all(
        pencere.yeterli_islem_mi is False
        for pencere in rapor.pencereler
    )


def test_sinyal_yoksa_sifir_performansli_pencereler_uretilir() -> None:
    rapor = RollingWindowAnalyzer().analiz_et(
        sembol="AAA.IS",
        fiyat_verisi=fiyat_verisi_olustur(12),
        sinyaller=(),
        backtest_yapilandirmasi=baz_ayar(),
        yapilandirma=RollingWindowConfig(
            pencere_bar_sayisi=6,
            adim_bar_sayisi=6,
            minimum_islem_sayisi=1,
        ),
    )

    assert rapor.pencere_sayisi == 2
    assert rapor.degerlendirilen_pencere_sayisi == 0
    assert rapor.pozitif_pencere_orani == 0.0
    assert all(
        pencere.islem_sayisi == 0
        and pencere.toplam_getiri_orani == 0.0
        and pencere.maksimum_dusus_orani == 0.0
        for pencere in rapor.pencereler
    )


def test_ayni_penceredeki_cakisan_islemler_filtrelenir() -> None:
    fiyatlar = fiyat_verisi_olustur(10)
    rapor = RollingWindowAnalyzer().analiz_et(
        sembol="AAA.IS",
        fiyat_verisi=fiyatlar,
        sinyaller=(
            sinyal_olustur(fiyatlar, 0),
            sinyal_olustur(fiyatlar, 1),
        ),
        backtest_yapilandirmasi=baz_ayar(
            elde_tutma_gunu=3
        ),
        yapilandirma=RollingWindowConfig(
            pencere_bar_sayisi=10,
            adim_bar_sayisi=5,
            minimum_islem_sayisi=1,
        ),
    )

    pencere = rapor.pencereler[0]
    assert pencere.sinyal_sayisi == 2
    assert pencere.islem_sayisi == 1


def test_farkli_sembol_sinyalleri_pencereye_dahil_edilmez() -> None:
    fiyatlar = fiyat_verisi_olustur(10)
    rapor = RollingWindowAnalyzer().analiz_et(
        sembol="AAA",
        fiyat_verisi=fiyatlar,
        sinyaller=(
            sinyal_olustur(fiyatlar, 0, sembol="AAA.IS"),
            sinyal_olustur(fiyatlar, 1, sembol="BBB.IS"),
        ),
        backtest_yapilandirmasi=baz_ayar(),
        yapilandirma=RollingWindowConfig(
            pencere_bar_sayisi=10,
            adim_bar_sayisi=5,
            minimum_islem_sayisi=1,
        ),
    )

    assert rapor.sembol == "AAA.IS"
    assert rapor.pencereler[0].sinyal_sayisi == 1
    assert rapor.pencereler[0].islem_sayisi == 1


def test_kisa_ve_tekrarlanan_tarihli_fiyat_verisi_reddedilir() -> None:
    analizci = RollingWindowAnalyzer()

    with pytest.raises(
        RollingWindowAnalysisError,
        match="pencere bar sayısından kısa",
    ):
        analizci.analiz_et(
            sembol="AAA.IS",
            fiyat_verisi=fiyat_verisi_olustur(5),
            sinyaller=(),
            backtest_yapilandirmasi=baz_ayar(),
            yapilandirma=RollingWindowConfig(
                pencere_bar_sayisi=6,
                adim_bar_sayisi=3,
            ),
        )

    tekrarlanan = fiyat_verisi_olustur(6)
    tekrarlanan.index = pd.to_datetime(
        [
            "2026-01-01",
            "2026-01-01",
            "2026-01-02",
            "2026-01-03",
            "2026-01-04",
            "2026-01-05",
        ]
    )

    with pytest.raises(
        RollingWindowAnalysisError,
        match="tekrarlanan tarihler",
    ):
        analizci.analiz_et(
            sembol="AAA.IS",
            fiyat_verisi=tekrarlanan,
            sinyaller=(),
            backtest_yapilandirmasi=baz_ayar(),
            yapilandirma=RollingWindowConfig(
                pencere_bar_sayisi=6,
                adim_bar_sayisi=3,
            ),
        )
