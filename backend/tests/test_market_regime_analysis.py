from __future__ import annotations

import pandas as pd
import pytest

from backend.app.backtest.backtest_models import (
    BacktestConfig,
    BacktestTrade,
    CIKIS_SURE_SONU,
)
from backend.app.backtest.market_regime_analysis import (
    MarketRegimeAnalysisError,
    MarketRegimeAnalyzer,
    MarketRegimeConfig,
    TREND_DUSUS,
    TREND_YATAY,
    TREND_YUKSELIS,
    VOLATILITE_NORMAL,
    VOLATILITE_YUKSEK,
)


GORUNUM = "Pozitif Teknik Görünüm"


def fiyat_verisi_olustur(
    kapanislar: list[float],
    araliklar: list[float] | None = None,
) -> pd.DataFrame:
    araliklar = araliklar or [1.0 for _ in kapanislar]

    return pd.DataFrame(
        {
            "Open": kapanislar,
            "High": [
                kapanis + gunluk_aralik
                for kapanis, gunluk_aralik in zip(
                    kapanislar,
                    araliklar,
                )
            ],
            "Low": [
                kapanis - gunluk_aralik
                for kapanis, gunluk_aralik in zip(
                    kapanislar,
                    araliklar,
                )
            ],
            "Close": kapanislar,
            "Volume": [
                1_000_000.0
                for _ in kapanislar
            ],
        },
        index=pd.date_range(
            "2026-01-01",
            periods=len(kapanislar),
            freq="D",
        ),
    )


def kisa_rejim_ayari() -> MarketRegimeConfig:
    return MarketRegimeConfig(
        hizli_ema_periyodu=2,
        yavas_ema_periyodu=4,
        egim_bakisi=1,
        minimum_ema_farki_orani=0.001,
        atr_periyodu=2,
        volatilite_bakisi=3,
        yuksek_volatilite_carpani=1.0,
    )


def backtest_ayari() -> BacktestConfig:
    return BacktestConfig(
        elde_tutma_gunu=2,
        minimum_skor=50,
        baslangic_sermayesi=100_000.0,
        pozisyon_orani=1.0,
        islem_maliyeti_orani=0.0,
        zarar_durdur_orani=None,
        hedef_orani=None,
    )


def islem_olustur(
    fiyatlar: pd.DataFrame,
    sinyal_konumu: int,
    giris_fiyati: float,
    cikis_fiyati: float,
    sembol: str = "AAA.IS",
) -> BacktestTrade:
    return BacktestTrade.olustur(
        sembol=sembol,
        sinyal_tarihi=fiyatlar.index[sinyal_konumu].date(),
        giris_tarihi=fiyatlar.index[sinyal_konumu + 1].date(),
        cikis_tarihi=fiyatlar.index[sinyal_konumu + 2].date(),
        giris_fiyati=giris_fiyati,
        cikis_fiyati=cikis_fiyati,
        skor=60,
        teknik_gorunum=GORUNUM,
        elde_tutulan_bar=2,
        cikis_nedeni=CIKIS_SURE_SONU,
        islem_maliyeti_orani=0.0,
    )


def nokta_bul(rapor, tarih):
    return next(
        nokta
        for nokta in rapor.gunluk_noktalar
        if nokta.tarih == tarih
    )


def test_rejim_yapilandirmasi_gecersiz_degerleri_reddeder() -> None:
    with pytest.raises(ValueError, match="Hızlı EMA"):
        MarketRegimeConfig(hizli_ema_periyodu=1)

    with pytest.raises(ValueError, match="Yavaş EMA"):
        MarketRegimeConfig(
            hizli_ema_periyodu=5,
            yavas_ema_periyodu=5,
        )

    with pytest.raises(ValueError, match="Eğim bakışı"):
        MarketRegimeConfig(egim_bakisi=0)

    with pytest.raises(ValueError, match="EMA farkı"):
        MarketRegimeConfig(minimum_ema_farki_orani=-0.1)

    with pytest.raises(ValueError, match="ATR periyodu"):
        MarketRegimeConfig(atr_periyodu=1)

    with pytest.raises(ValueError, match="Volatilite bakışı"):
        MarketRegimeConfig(volatilite_bakisi=1)

    with pytest.raises(ValueError, match="volatilite çarpanı"):
        MarketRegimeConfig(yuksek_volatilite_carpani=0.0)


def test_yukselis_dusus_ve_yatay_trendler_siniflandirilir() -> None:
    analizci = MarketRegimeAnalyzer()
    ayarlar = kisa_rejim_ayari()

    yukselis = fiyat_verisi_olustur(
        [100.0 + konum for konum in range(12)]
    )
    dusus = fiyat_verisi_olustur(
        [112.0 - konum for konum in range(12)]
    )
    yatay = fiyat_verisi_olustur(
        [100.0 for _ in range(12)]
    )

    yukselis_raporu = analizci.analiz_et(
        sembol="AAA",
        fiyat_verisi=yukselis,
        islemler=(),
        backtest_yapilandirmasi=backtest_ayari(),
        yapilandirma=ayarlar,
    )
    dusus_raporu = analizci.analiz_et(
        sembol="AAA",
        fiyat_verisi=dusus,
        islemler=(),
        backtest_yapilandirmasi=backtest_ayari(),
        yapilandirma=ayarlar,
    )
    yatay_raporu = analizci.analiz_et(
        sembol="AAA",
        fiyat_verisi=yatay,
        islemler=(),
        backtest_yapilandirmasi=backtest_ayari(),
        yapilandirma=ayarlar,
    )

    assert yukselis_raporu.gunluk_noktalar[-1].trend_rejimi == (
        TREND_YUKSELIS
    )
    assert dusus_raporu.gunluk_noktalar[-1].trend_rejimi == (
        TREND_DUSUS
    )
    assert yatay_raporu.gunluk_noktalar[-1].trend_rejimi == (
        TREND_YATAY
    )


def test_atr_hareketli_medyani_yuksek_volatiliteyi_ayirir() -> None:
    fiyatlar = fiyat_verisi_olustur(
        [100.0 for _ in range(12)],
        araliklar=[1.0] * 11 + [10.0],
    )
    rapor = MarketRegimeAnalyzer().analiz_et(
        sembol="AAA.IS",
        fiyat_verisi=fiyatlar,
        islemler=(),
        backtest_yapilandirmasi=backtest_ayari(),
        yapilandirma=kisa_rejim_ayari(),
    )

    assert rapor.gunluk_noktalar[0].volatilite_rejimi == (
        VOLATILITE_NORMAL
    )
    assert rapor.gunluk_noktalar[-1].volatilite_rejimi == (
        VOLATILITE_YUKSEK
    )
    assert (
        rapor.gunluk_noktalar[-1].atr_orani
        > rapor.gunluk_noktalar[-1].volatilite_esigi_orani
    )


def test_sinyal_gunu_rejimi_gelecek_fiyatlardan_etkilenmez() -> None:
    ortak = [100.0 + konum for konum in range(9)]
    fiyatlar_a = fiyat_verisi_olustur(
        ortak + [109.0, 110.0, 111.0]
    )
    fiyatlar_b = fiyat_verisi_olustur(
        ortak + [70.0, 60.0, 50.0],
        araliklar=[1.0] * 9 + [20.0, 20.0, 20.0],
    )
    sinyal_tarihi = fiyatlar_a.index[8].date()
    analizci = MarketRegimeAnalyzer()

    rapor_a = analizci.analiz_et(
        sembol="AAA.IS",
        fiyat_verisi=fiyatlar_a,
        islemler=(),
        backtest_yapilandirmasi=backtest_ayari(),
        yapilandirma=kisa_rejim_ayari(),
    )
    rapor_b = analizci.analiz_et(
        sembol="AAA.IS",
        fiyat_verisi=fiyatlar_b,
        islemler=(),
        backtest_yapilandirmasi=backtest_ayari(),
        yapilandirma=kisa_rejim_ayari(),
    )

    nokta_a = nokta_bul(rapor_a, sinyal_tarihi)
    nokta_b = nokta_bul(rapor_b, sinyal_tarihi)

    assert nokta_a.trend_rejimi == nokta_b.trend_rejimi
    assert nokta_a.volatilite_rejimi == nokta_b.volatilite_rejimi
    assert nokta_a.hizli_ema == pytest.approx(nokta_b.hizli_ema)
    assert nokta_a.atr_orani == pytest.approx(nokta_b.atr_orani)


def test_rejim_bazli_islem_performansi_hesaplanir() -> None:
    fiyatlar = fiyat_verisi_olustur(
        [100.0 + konum for konum in range(14)]
    )
    islemler = (
        islem_olustur(fiyatlar, 6, 100.0, 110.0),
        islem_olustur(fiyatlar, 9, 100.0, 90.0),
    )
    rapor = MarketRegimeAnalyzer().analiz_et(
        sembol="AAA",
        fiyat_verisi=fiyatlar,
        islemler=islemler,
        backtest_yapilandirmasi=backtest_ayari(),
        yapilandirma=kisa_rejim_ayari(),
    )
    yukselis = next(
        sonuc
        for sonuc in rapor.trend_performanslari
        if sonuc.rejim_adi == TREND_YUKSELIS
    )

    assert rapor.toplam_islem_sayisi == 2
    assert rapor.siniflandirilan_islem_sayisi == 2
    assert rapor.siniflandirma_orani == 1.0
    assert yukselis.islem_sayisi == 2
    assert yukselis.kazanan_islem_sayisi == 1
    assert yukselis.kaybeden_islem_sayisi == 1
    assert yukselis.kazanma_orani == pytest.approx(0.5)
    assert yukselis.toplam_net_getiri_orani == pytest.approx(-0.01)
    assert yukselis.kar_faktoru == pytest.approx(1.0)


def test_yeterli_gecmis_olmayan_islem_siniflandirilamaz() -> None:
    fiyatlar = fiyat_verisi_olustur(
        [100.0 + konum for konum in range(12)]
    )
    rapor = MarketRegimeAnalyzer().analiz_et(
        sembol="AAA.IS",
        fiyat_verisi=fiyatlar,
        islemler=(
            islem_olustur(fiyatlar, 0, 100.0, 101.0),
        ),
        backtest_yapilandirmasi=backtest_ayari(),
        yapilandirma=kisa_rejim_ayari(),
    )

    assert rapor.toplam_islem_sayisi == 1
    assert rapor.siniflandirilan_islem_sayisi == 0
    assert rapor.siniflandirilamayan_islem_sayisi == 1
    assert rapor.siniflandirma_orani == 0.0
    assert rapor.en_iyi_birlesik_rejim is None


def test_farkli_sembol_islemleri_rapora_dahil_edilmez() -> None:
    fiyatlar = fiyat_verisi_olustur(
        [100.0 + konum for konum in range(12)]
    )
    rapor = MarketRegimeAnalyzer().analiz_et(
        sembol="AAA",
        fiyat_verisi=fiyatlar,
        islemler=(
            islem_olustur(
                fiyatlar,
                6,
                100.0,
                110.0,
                sembol="BBB.IS",
            ),
        ),
        backtest_yapilandirmasi=backtest_ayari(),
        yapilandirma=kisa_rejim_ayari(),
    )

    assert rapor.sembol == "AAA.IS"
    assert rapor.toplam_islem_sayisi == 0
    assert rapor.siniflandirilan_islem_sayisi == 0
    assert all(
        sonuc.islem_sayisi == 0
        for sonuc in rapor.birlesik_performanslar
    )


def test_eksik_ve_tekrarlanan_fiyat_verisi_reddedilir() -> None:
    analizci = MarketRegimeAnalyzer()

    with pytest.raises(
        MarketRegimeAnalysisError,
        match="Eksik fiyat sütunları",
    ):
        analizci.analiz_et(
            sembol="AAA.IS",
            fiyat_verisi=pd.DataFrame(
                {"Close": [100.0, 101.0]},
                index=pd.date_range(
                    "2026-01-01",
                    periods=2,
                ),
            ),
            islemler=(),
            backtest_yapilandirmasi=backtest_ayari(),
            yapilandirma=kisa_rejim_ayari(),
        )

    tekrarlanan = fiyat_verisi_olustur(
        [100.0 for _ in range(6)]
    )
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
        MarketRegimeAnalysisError,
        match="tekrarlanan tarihler",
    ):
        analizci.analiz_et(
            sembol="AAA.IS",
            fiyat_verisi=tekrarlanan,
            islemler=(),
            backtest_yapilandirmasi=backtest_ayari(),
            yapilandirma=kisa_rejim_ayari(),
        )
