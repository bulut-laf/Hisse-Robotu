from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backend.app.backtest.backtest_models import (
    BacktestTrade,
    CIKIS_SURE_SONU,
)
from backend.app.backtest.daily_equity_curve import (
    DailyEquityCurveAnalyzer,
    DailyEquityCurveError,
)


GORUNUM = "Pozitif Teknik Görünüm"


def fiyat_verisi_olustur(
    kapanislar: list[float],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": kapanislar,
            "High": [fiyat + 1.0 for fiyat in kapanislar],
            "Low": [fiyat - 1.0 for fiyat in kapanislar],
            "Close": kapanislar,
            "Volume": [1_000_000.0 for _ in kapanislar],
        },
        index=pd.date_range(
            start="2026-01-01",
            periods=len(kapanislar),
            freq="D",
        ),
    )


def islem_olustur(
    sinyal_tarihi: date,
    giris_tarihi: date,
    cikis_tarihi: date,
    giris_fiyati: float,
    cikis_fiyati: float,
    maliyet: float = 0.0,
) -> BacktestTrade:
    return BacktestTrade.olustur(
        sembol="AAA.IS",
        sinyal_tarihi=sinyal_tarihi,
        giris_tarihi=giris_tarihi,
        cikis_tarihi=cikis_tarihi,
        giris_fiyati=giris_fiyati,
        cikis_fiyati=cikis_fiyati,
        skor=70,
        teknik_gorunum=GORUNUM,
        elde_tutulan_bar=max(
            1,
            (cikis_tarihi - giris_tarihi).days + 1,
        ),
        cikis_nedeni=CIKIS_SURE_SONU,
        islem_maliyeti_orani=maliyet,
    )


def test_islem_yoksa_bos_rapor_uretilir() -> None:
    rapor = DailyEquityCurveAnalyzer().analiz_et(
        fiyat_verisi=fiyat_verisi_olustur([100.0, 101.0]),
        islemler=(),
        baslangic_sermayesi=100_000.0,
    )

    assert rapor.noktalar == ()
    assert rapor.baslangic_tarihi is None
    assert rapor.bitis_tarihi is None
    assert rapor.bitis_sermayesi == 100_000.0
    assert rapor.maksimum_dusus_orani == 0.0


def test_gunluk_noktalar_ve_bitis_sermayesi_hesaplanir() -> None:
    birinci = islem_olustur(
        sinyal_tarihi=date(2025, 12, 31),
        giris_tarihi=date(2026, 1, 1),
        cikis_tarihi=date(2026, 1, 3),
        giris_fiyati=100.0,
        cikis_fiyati=120.0,
    )

    ikinci = islem_olustur(
        sinyal_tarihi=date(2026, 1, 3),
        giris_tarihi=date(2026, 1, 4),
        cikis_tarihi=date(2026, 1, 5),
        giris_fiyati=110.0,
        cikis_fiyati=130.0,
    )

    rapor = DailyEquityCurveAnalyzer().analiz_et(
        fiyat_verisi=fiyat_verisi_olustur(
            [100.0, 80.0, 120.0, 110.0, 130.0]
        ),
        islemler=(birinci, ikinci),
        baslangic_sermayesi=100_000.0,
        pozisyon_orani=1.0,
        islem_maliyeti_orani=0.0,
    )

    beklenen = 100_000.0 * 1.20 * (130.0 / 110.0)

    assert rapor.islem_gunu_sayisi == 5
    assert rapor.baslangic_tarihi == date(2026, 1, 1)
    assert rapor.bitis_tarihi == date(2026, 1, 5)
    assert rapor.bitis_sermayesi == pytest.approx(beklenen)
    assert rapor.noktalar[0].islem_sirasi == 1
    assert rapor.noktalar[-1].islem_sirasi == 2


def test_islem_ici_dusus_gunluk_raporda_yakalanir() -> None:
    islem = islem_olustur(
        sinyal_tarihi=date(2025, 12, 31),
        giris_tarihi=date(2026, 1, 1),
        cikis_tarihi=date(2026, 1, 3),
        giris_fiyati=100.0,
        cikis_fiyati=110.0,
    )

    rapor = DailyEquityCurveAnalyzer().analiz_et(
        fiyat_verisi=fiyat_verisi_olustur(
            [100.0, 50.0, 110.0]
        ),
        islemler=(islem,),
        baslangic_sermayesi=100_000.0,
        pozisyon_orani=1.0,
        islem_maliyeti_orani=0.0,
    )

    assert rapor.maksimum_dusus_orani == pytest.approx(0.50)
    assert rapor.maksimum_dusus_donemi is not None
    assert (
        rapor.maksimum_dusus_donemi.dip_tarihi
        == date(2026, 1, 2)
    )
    assert (
        rapor.maksimum_dusus_donemi.toparlanma_tarihi
        == date(2026, 1, 3)
    )


def test_pozisyon_orani_ve_islem_maliyeti_uygulanir() -> None:
    maliyet = 0.01
    islem = islem_olustur(
        sinyal_tarihi=date(2025, 12, 31),
        giris_tarihi=date(2026, 1, 1),
        cikis_tarihi=date(2026, 1, 2),
        giris_fiyati=100.0,
        cikis_fiyati=110.0,
        maliyet=maliyet,
    )

    rapor = DailyEquityCurveAnalyzer().analiz_et(
        fiyat_verisi=fiyat_verisi_olustur([100.0, 110.0]),
        islemler=(islem,),
        baslangic_sermayesi=100_000.0,
        pozisyon_orani=0.50,
        islem_maliyeti_orani=maliyet,
    )

    net_getiri = (110.0 * 0.99) / (100.0 * 1.01) - 1.0
    beklenen = 100_000.0 * (1.0 + 0.50 * net_getiri)

    assert rapor.bitis_sermayesi == pytest.approx(beklenen)
    assert (
        rapor.toplam_bilesik_getiri_orani
        == pytest.approx(0.50 * net_getiri)
    )


def test_acik_dusus_donemi_son_gune_kadar_uzar() -> None:
    islem = islem_olustur(
        sinyal_tarihi=date(2025, 12, 31),
        giris_tarihi=date(2026, 1, 1),
        cikis_tarihi=date(2026, 1, 3),
        giris_fiyati=100.0,
        cikis_fiyati=80.0,
    )

    rapor = DailyEquityCurveAnalyzer().analiz_et(
        fiyat_verisi=fiyat_verisi_olustur(
            [100.0, 90.0, 80.0]
        ),
        islemler=(islem,),
        islem_maliyeti_orani=0.0,
    )

    maksimum = rapor.maksimum_dusus_donemi

    assert maksimum is not None
    assert maksimum.toparlanma_tarihi is None
    assert maksimum.zirve_altinda_gun_sayisi == 2
    assert rapor.guncel_dusus_orani == pytest.approx(0.20)


def test_gecersiz_veri_ve_cakisan_islemler_hata_verir() -> None:
    analizci = DailyEquityCurveAnalyzer()
    birinci = islem_olustur(
        sinyal_tarihi=date(2025, 12, 31),
        giris_tarihi=date(2026, 1, 1),
        cikis_tarihi=date(2026, 1, 3),
        giris_fiyati=100.0,
        cikis_fiyati=110.0,
    )
    cakisan = islem_olustur(
        sinyal_tarihi=date(2026, 1, 1),
        giris_tarihi=date(2026, 1, 2),
        cikis_tarihi=date(2026, 1, 3),
        giris_fiyati=90.0,
        cikis_fiyati=95.0,
    )

    with pytest.raises(
        DailyEquityCurveError,
        match="çakışmayan",
    ):
        analizci.analiz_et(
            fiyat_verisi=fiyat_verisi_olustur(
                [100.0, 90.0, 110.0]
            ),
            islemler=(birinci, cakisan),
            islem_maliyeti_orani=0.0,
        )

    with pytest.raises(
        DailyEquityCurveError,
        match="Close sütunu",
    ):
        analizci.analiz_et(
            fiyat_verisi=pd.DataFrame(
                {"Open": [100.0, 110.0]},
                index=pd.date_range(
                    "2026-01-01",
                    periods=2,
                ),
            ),
            islemler=(birinci,),
        )
