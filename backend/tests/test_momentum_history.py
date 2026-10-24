from __future__ import annotations

from pathlib import Path

from dataclasses import replace

from backend.app.analysis.momentum_discovery import (
    SINIF_HACIM_BIRIKIMI,
    SINIF_IZLEME_DISI,
    SINIF_KALICI_HAZIRLIK,
    MomentumCandidate,
)
from backend.app.history.momentum_history import MomentumHistoryStore


def aday(tarih: str, fiyat: float) -> MomentumCandidate:
    return MomentumCandidate(
        sembol="AAA.IS",
        analiz_tarihi=tarih,
        kapanis=fiyat,
        momentum_skoru=70,
        sinif="A — Erken Keşif",
        goreceli_guc_puani=15,
        fiyat_ivmesi_puani=10,
        hacim_birikimi_puani=10,
        kirilim_hazirligi_puani=10,
        trend_puani=10,
        likidite_puani=8,
        risk_kalitesi_puani=7,
        getiri_5g=0.02,
        getiri_20g=0.05,
        getiri_60g=0.10,
        hacim_orani=1.2,
        yirmi_gunluk_zirve_uzakligi=0.03,
        ortalama_tl_hacim=50_000_000,
        rsi14=58,
        atr_yuzde=3,
        teknik_skor=60,
        teknik_gorunum="Nötr Teknik Görünüm",
        risk_odul_orani=2,
        risk_odul_uygun=True,
        kirilim=False,
        sikisma=True,
        asiri_uzamis=False,
        pozitif_nedenler=("test",),
        riskler=(),
    )


def test_ilk_kayitta_bir_gun_ve_sifir_getiri(tmp_path: Path) -> None:
    depo = MomentumHistoryStore(tmp_path)
    zengin = depo.zenginlestir((aday("2026-07-24", 100.0),))[0]

    assert zengin.listedeki_gun == 1
    assert zengin.ilk_gorulme_fiyati == 100.0
    assert zengin.ilk_gorulmeden_getiri == 0.0


def test_gecmis_kaydi_sonraki_taramayi_zenginlestirir(tmp_path: Path) -> None:
    depo = MomentumHistoryStore(tmp_path)
    ilk = depo.zenginlestir((aday("2026-07-24", 100.0),))
    depo.kaydet(ilk)

    ikinci = depo.zenginlestir((aday("2026-07-27", 110.0),))[0]

    assert ikinci.listedeki_gun == 2
    assert ikinci.ilk_gorulme_tarihi == "2026-07-24"
    assert round(ikinci.ilk_gorulmeden_getiri, 4) == 0.10


def test_izleme_disi_hisse_yakin_hazirlik_gecmisiyle_kalici_olur(tmp_path: Path) -> None:
    depo = MomentumHistoryStore(tmp_path)
    ilk = replace(aday("2026-07-01", 100.0), sinif=SINIF_HACIM_BIRIKIMI)
    ikinci = replace(aday("2026-07-06", 101.0), sinif=SINIF_HACIM_BIRIKIMI)
    depo.kaydet((ilk, ikinci))

    guncel = replace(
        aday("2026-07-10", 99.0),
        sinif=SINIF_IZLEME_DISI,
        izleme_disi_nedeni="Günlük koşullar zayıfladı.",
    )
    zengin = depo.zenginlestir((guncel,))[0]

    assert zengin.sinif == SINIF_KALICI_HAZIRLIK
    assert zengin.kalici_hazirlik is True
    assert zengin.son_hazirlik_sinyali_tarihi == "2026-07-06"
    assert len(zengin.sinyal_gecmisi) == 3
    assert "Kalıcı hazırlık" in zengin.hazirlik_durumu


def test_eski_hazirlik_sinyali_kalici_aday_yapmaz(tmp_path: Path) -> None:
    depo = MomentumHistoryStore(tmp_path)
    eski1 = replace(aday("2026-05-01", 100.0), sinif=SINIF_HACIM_BIRIKIMI)
    eski2 = replace(aday("2026-05-08", 101.0), sinif=SINIF_HACIM_BIRIKIMI)
    depo.kaydet((eski1, eski2))

    guncel = replace(aday("2026-07-10", 99.0), sinif=SINIF_IZLEME_DISI)
    zengin = depo.zenginlestir((guncel,))[0]

    assert zengin.sinif == SINIF_IZLEME_DISI
    assert zengin.kalici_hazirlik is False
