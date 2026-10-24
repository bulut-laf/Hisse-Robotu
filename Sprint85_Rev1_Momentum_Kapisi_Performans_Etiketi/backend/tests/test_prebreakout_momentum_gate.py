from dataclasses import replace

from backend.app.prebreakout.prebreakout_features import ozellikleri_hesapla
from backend.app.prebreakout.prebreakout_models import PreBreakoutStage
from backend.app.prebreakout.prebreakout_stage import asamayi_belirle
from backend.tests.prebreakout_test_helpers import ornek_veri


def test_negatif_macd_egimi_yuksek_skoru_e1_ile_sinirlar() -> None:
    features = ozellikleri_hesapla(ornek_veri())
    weak = replace(
        features,
        macd_histogram_egimi=-0.30,
        rsi_egimi=2.0,
        direnc_uzaklik_pct=3.0,
    )

    stage = asamayi_belirle(
        72,
        weak,
        late_entry=False,
        momentum_score=14,
    )

    assert stage is PreBreakoutStage.E1


def test_momentum_bileseni_onun_altindaysa_e2_uretmez() -> None:
    features = ozellikleri_hesapla(ornek_veri())
    ready = replace(
        features,
        macd_histogram_egimi=0.20,
        rsi_egimi=2.0,
        direnc_uzaklik_pct=4.0,
    )

    stage = asamayi_belirle(
        65,
        ready,
        late_entry=False,
        momentum_score=9,
    )

    assert stage is PreBreakoutStage.E1


def test_e3_icin_macd_ve_rsi_egimi_pozitif_olmalidir() -> None:
    features = ozellikleri_hesapla(ornek_veri())
    ready = replace(
        features,
        macd_histogram_egimi=0.20,
        rsi_egimi=1.5,
        direnc_uzaklik_pct=3.0,
    )

    stage = asamayi_belirle(
        74,
        ready,
        late_entry=False,
        momentum_score=12,
    )

    assert stage is PreBreakoutStage.E3


def test_rsi_egimi_negatifse_e3_e2ye_indirilir() -> None:
    features = ozellikleri_hesapla(ornek_veri())
    weak_rsi = replace(
        features,
        macd_histogram_egimi=0.20,
        rsi_egimi=-1.0,
        direnc_uzaklik_pct=3.0,
    )

    stage = asamayi_belirle(
        74,
        weak_rsi,
        late_entry=False,
        momentum_score=12,
    )

    assert stage is PreBreakoutStage.E2
