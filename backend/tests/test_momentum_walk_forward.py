from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from backend.app.analysis.momentum_discovery import MomentumDiscoveryEngine
from backend.app.analysis.momentum_walk_forward import (
    MomentumWalkForwardEngine,
    MomentumWalkForwardRequest,
    sinyal_gecmisi_tablosu,
    walk_forward_tablosu,
)


class SahteAnalizMotoru:
    def veriden_analiz_et(self, sembol: str, fiyat_verisi: pd.DataFrame) -> object:
        return SimpleNamespace(
            sinyal=SimpleNamespace(skor=70, karar="Pozitif Teknik Görünüm"),
            risk_plani=SimpleNamespace(risk_odul_orani=2.0, filtreyi_gecti=True),
        )


def tarihsel_veri() -> pd.DataFrame:
    bar = 150
    x = np.arange(bar, dtype=float)
    kapanis = 40.0 + x * 0.04 + np.sin(x / 4.0) * 0.5
    # Kesim öncesinde dirence yakın, sıkışan ve hacim biriktiren yapı.
    direnc = float(kapanis[90:110].max())
    kapanis[110:120] = np.linspace(direnc * 0.96, direnc * 0.99, 10)
    # Gelecek hareket yalnızca performans ölçümünde kullanılacak.
    kapanis[120:] = np.linspace(kapanis[119] * 1.01, kapanis[119] * 1.18, 30)
    hacim = np.full(bar, 1_000_000.0)
    hacim[110:120] = np.linspace(1_050_000.0, 1_500_000.0, 10)
    hacim[120:] = 2_000_000.0
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


def test_walk_forward_gelecek_veriyi_gizler_ve_performansi_olcer() -> None:
    veri = tarihsel_veri()
    kesim = str(veri.index[119].date())
    motor = MomentumWalkForwardEngine(
        MomentumDiscoveryEngine(analiz_motoru=SahteAnalizMotoru())  # type: ignore[arg-type]
    )

    sonuclar, hatalar = motor.calistir(
        {"AAA.IS": veri},
        kesim_tarihi=kesim,
        ufuklar=(5, 10, 20),
    )

    assert hatalar == ()
    assert len(sonuclar) == 1
    assert sonuclar[0].aday.analiz_tarihi == kesim
    assert sonuclar[0].getiri(5) is not None
    assert sonuclar[0].getiri(20) is not None
    assert sonuclar[0].maksimum_olumlu_hareket is not None
    assert sonuclar[0].maksimum_olumlu_hareket > 0.10
    assert sonuclar[0].maksimum_fiyat is not None
    assert sonuclar[0].maksimum_fiyat > float(veri.iloc[119]["Close"])
    assert sonuclar[0].maksimum_fiyat_tarihi
    assert sonuclar[0].maksimum_ters_hareket is not None
    assert sonuclar[0].maksimum_ters_hareket >= 0


def test_walk_forward_yetersiz_kesim_gecmisini_hata_yapar() -> None:
    veri = tarihsel_veri()
    kesim = str(veri.index[40].date())
    motor = MomentumWalkForwardEngine(
        MomentumDiscoveryEngine(analiz_motoru=SahteAnalizMotoru())  # type: ignore[arg-type]
    )

    sonuclar, hatalar = motor.calistir({"AAA.IS": veri}, kesim_tarihi=kesim)

    assert sonuclar == ()
    assert len(hatalar) == 1
    assert "en az 80" in hatalar[0].hata


def test_walk_forward_istegi_gecersiz_tarihi_reddeder() -> None:
    with pytest.raises(ValueError, match="YYYY-AA-GG"):
        MomentumWalkForwardRequest(kesim_tarihi="27/07/2026")


def test_walk_forward_tablosu_ileri_ufuklari_gosterir() -> None:
    veri = tarihsel_veri()
    kesim = str(veri.index[119].date())
    motor = MomentumWalkForwardEngine(
        MomentumDiscoveryEngine(analiz_motoru=SahteAnalizMotoru())  # type: ignore[arg-type]
    )
    sonuclar, _ = motor.calistir({"AAA.IS": veri}, kesim_tarihi=kesim)
    sonuc = SimpleNamespace(sonuclar=sonuclar)

    tablo = walk_forward_tablosu(sonuc)  # type: ignore[arg-type]

    assert tablo[0]["Hisse"] == "AAA"
    assert "5G kapanış (%)" in tablo[0]
    assert "Dönem içi en yüksek" in tablo[0]
    assert "Gerçek azami yükseliş (%)" in tablo[0]
    assert "Yakın direnç" in tablo[0]
    assert "Kırılım tetiği" in tablo[0]


def test_walk_forward_sinyal_gecmisini_haftalik_adimlarla_uretir() -> None:
    veri = tarihsel_veri()
    kesim = str(veri.index[119].date())
    motor = MomentumWalkForwardEngine(
        MomentumDiscoveryEngine(analiz_motoru=SahteAnalizMotoru())  # type: ignore[arg-type]
    )

    sonuclar, hatalar = motor.calistir(
        {"AAA.IS": veri},
        kesim_tarihi=kesim,
        sinyal_gecmisi_olustur=True,
        sinyal_gecmisi_adim_sayisi=4,
        sinyal_gecmisi_adim_bari=5,
    )

    assert hatalar == ()
    assert len(sonuclar[0].sinyal_gecmisi) == 4
    tablo = sinyal_gecmisi_tablosu(sonuclar[0])
    assert len(tablo) == 4
    assert "Kırılım tetiği" in tablo[-1]
    assert tablo[-1]["Tarih"] == kesim
