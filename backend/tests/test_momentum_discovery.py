from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from backend.app.analysis.momentum_discovery import (
    SINIF_ASIRI_YUKSELMIS,
    SINIF_DIRENCE_YAKLASIYOR,
    SINIF_ERKEN_UYARI,
    SINIF_ISLEME_HAZIR,
    MomentumDiscoveryEngine,
    MomentumDiscoveryRequest,
    MomentumDiscoveryService,
    momentum_aday_tablosu,
)
from backend.app.data.batch_market_data import BatchMarketDataResult
from backend.app.history.momentum_history import MomentumHistoryStore


class SahteAnalizMotoru:
    def veriden_analiz_et(self, sembol: str, fiyat_verisi: pd.DataFrame) -> object:
        return SimpleNamespace(
            sinyal=SimpleNamespace(
                skor=75,
                karar="Pozitif Teknik Görünüm",
            ),
            risk_plani=SimpleNamespace(
                risk_odul_orani=2.20,
                filtreyi_gecti=True,
            ),
        )


def fiyat_verisi(*, kirilim: bool = False, asiri: bool = False) -> pd.DataFrame:
    bar = 180
    x = np.arange(bar, dtype=float)
    kapanis = 50.0 + x * 0.05 + np.sin(x / 7.0) * 0.4
    if kirilim:
        kapanis[-1] = kapanis[-20:-1].max() * 1.03
    if asiri:
        kapanis[-5:] *= np.linspace(1.0, 1.35, 5)
    hacim = np.full(bar, 1_500_000.0)
    hacim[-5:] = 3_000_000.0
    return pd.DataFrame(
        {
            "Open": kapanis - 0.10,
            "High": kapanis + 0.40,
            "Low": kapanis - 0.40,
            "Close": kapanis,
            "Volume": hacim,
        },
        index=pd.bdate_range("2025-01-01", periods=bar),
    )


def test_momentum_motoru_c_e2_ve_d_siniflarini_uretir() -> None:
    motor = MomentumDiscoveryEngine(analiz_motoru=SahteAnalizMotoru())  # type: ignore[arg-type]

    adaylar, hatalar = motor.analiz_et(
        {
            "AAA.IS": fiyat_verisi(kirilim=True),
            "BBB.IS": fiyat_verisi(),
            "CCC.IS": fiyat_verisi(asiri=True),
        }
    )

    siniflar = {aday.sembol: aday.sinif for aday in adaylar}
    assert siniflar["AAA.IS"] == SINIF_ISLEME_HAZIR
    assert siniflar["BBB.IS"] == SINIF_DIRENCE_YAKLASIYOR
    assert siniflar["CCC.IS"] == SINIF_ASIRI_YUKSELMIS
    assert hatalar == ()


def erken_uyari_verisi() -> pd.DataFrame:
    bar = 180
    x = np.arange(bar, dtype=float)
    kapanis = 50.0 + x * 0.03 + np.sin(x / 4.0) * 0.6
    onceki_direnc = float(kapanis[-30:-10].max())
    kapanis[-10:] = np.linspace(onceki_direnc * 0.96, onceki_direnc * 0.99, 10)
    hacim = np.full(bar, 1_500_000.0)
    hacim[-10:] = np.linspace(1_600_000.0, 1_950_000.0, 10)
    return pd.DataFrame(
        {
            "Open": kapanis - 0.10,
            "High": kapanis + 0.15,
            "Low": kapanis - 0.15,
            "Close": kapanis,
            "Volume": hacim,
        },
        index=pd.bdate_range("2025-01-01", periods=bar),
    )


def test_kirilim_oncesi_e3_erken_uyari_uretilir() -> None:
    motor = MomentumDiscoveryEngine(analiz_motoru=SahteAnalizMotoru())  # type: ignore[arg-type]

    adaylar, hatalar = motor.analiz_et({"ERKEN.IS": erken_uyari_verisi()})

    assert hatalar == ()
    assert adaylar[0].sinif == SINIF_ERKEN_UYARI
    assert adaylar[0].kirilim is False
    assert adaylar[0].yirmi_gunluk_zirve_uzakligi <= 0.03
    assert adaylar[0].hacim_egimi > 1.0
    assert "direnç" in adaylar[0].hazirlik_durumu.lower()


def test_momentum_puani_bilesenleri_100u_gecmez() -> None:
    motor = MomentumDiscoveryEngine(analiz_motoru=SahteAnalizMotoru())  # type: ignore[arg-type]
    adaylar, _ = motor.analiz_et({"AAA.IS": fiyat_verisi(kirilim=True)})
    aday = adaylar[0]

    assert 0 <= aday.momentum_skoru <= 100
    assert aday.goreceli_guc_puani <= 20
    assert aday.fiyat_ivmesi_puani <= 15
    assert aday.hacim_birikimi_puani <= 15
    assert aday.kirilim_hazirligi_puani <= 15
    assert aday.trend_puani <= 15
    assert aday.likidite_puani <= 10
    assert aday.risk_kalitesi_puani <= 10
    assert aday.kirilim_tetik_seviyesi > aday.yakin_direnc


def test_yetersiz_veri_hata_olarak_korunur() -> None:
    motor = MomentumDiscoveryEngine(analiz_motoru=SahteAnalizMotoru())  # type: ignore[arg-type]
    adaylar, hatalar = motor.analiz_et({"KISA.IS": fiyat_verisi().tail(40)})

    assert adaylar == ()
    assert len(hatalar) == 1
    assert "80 işlem günü" in hatalar[0].hata


def test_gecersiz_momentum_istegi_reddedilir() -> None:
    with pytest.raises(ValueError, match="Minimum momentum"):
        MomentumDiscoveryRequest(minimum_skor=101)


class SahteEvrenDeposu:
    def evreni_yukle(self, evren_adi: str, internetten_guncelle: bool = True) -> object:
        return SimpleNamespace(
            semboller=("AAA.IS", "BBB.IS", "CCC.IS"),
            kaynak="Test evreni",
            tarih="2026-07-27",
        )


def test_momentum_servisi_filtreler_gecmise_kaydeder(tmp_path: Path) -> None:
    veriler = {
        "AAA.IS": fiyat_verisi(kirilim=True),
        "BBB.IS": fiyat_verisi(),
        "CCC.IS": fiyat_verisi(asiri=True),
    }

    def veri_getirici(semboller: object, **_: object) -> BatchMarketDataResult:
        assert tuple(semboller) == ("AAA.IS", "BBB.IS", "CCC.IS")
        return BatchMarketDataResult(veriler=veriler, hatalar=())

    servis = MomentumDiscoveryService(
        evren_repository=SahteEvrenDeposu(),  # type: ignore[arg-type]
        veri_getirici=veri_getirici,
        motor=MomentumDiscoveryEngine(analiz_motoru=SahteAnalizMotoru()),  # type: ignore[arg-type]
        gecmis_deposu=MomentumHistoryStore(tmp_path / "gecmis"),
    )
    sonuc = servis.calistir(
        MomentumDiscoveryRequest(
            evren="BIST 100",
            minimum_skor=55,
            maksimum_aday=10,
        )
    )

    assert sonuc.evren_sembol_sayisi == 3
    assert len(sonuc.adaylar) == 2
    assert len(sonuc.asiri_yukselmisler) == 1
    assert sonuc.kayit_yolu is not None
    assert Path(sonuc.kayit_yolu).is_file()

    tablo = momentum_aday_tablosu(sonuc)
    assert tablo[0]["Hisse"] == "AAA"
    assert "Momentum" in tablo[0]
    assert "Listede gün" in tablo[0]


def test_izleme_disi_aday_aciklayici_neden_uretir() -> None:
    motor = MomentumDiscoveryEngine(analiz_motoru=SahteAnalizMotoru())  # type: ignore[arg-type]
    zayif = fiyat_verisi()
    zayif["Volume"] = 100_000.0
    zayif.iloc[-20:, zayif.columns.get_loc("Close")] *= 0.85

    adaylar, hatalar = motor.analiz_et({"ZAYIF.IS": zayif})

    assert hatalar == ()
    assert adaylar[0].izleme_disi_nedeni
