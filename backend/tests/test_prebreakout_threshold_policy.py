from types import SimpleNamespace

import pytest

from backend.app.prebreakout.prebreakout_calibration import (
    PreBreakoutThresholdValidationRow,
    dogrulanmis_esik_politikasi_olustur,
)
from backend.app.prebreakout.prebreakout_models import PreBreakoutStage
from backend.app.prebreakout.prebreakout_stage import asamayi_belirle
from backend.app.prebreakout.prebreakout_threshold_policy import (
    PreBreakoutThresholdPolicy,
)


def features(*, macd=0.2, rsi=0.1, distance=4.0, volume=1.1):
    return SimpleNamespace(
        macd_histogram_egimi=macd,
        rsi_egimi=rsi,
        direnc_uzaklik_pct=distance,
        hacim_orani_3_10=volume,
    )


def validation(stage="E3", proposed=15, verdict="Kontrollü uygulama adayı"):
    return PreBreakoutThresholdValidationRow(
        stage=stage,
        current_minimum_momentum_score=10,
        proposed_minimum_momentum_score=proposed,
        baseline_measured_count=20,
        baseline_success_rate_pct=50.0,
        candidate_measured_count=12,
        candidate_success_rate_pct=80.0,
        success_rate_delta_pct=30.0,
        candidate_confidence_low_pct=51.0,
        sample_retention_pct=60.0,
        verdict=verdict,
        auto_apply=False,
    )


def test_politika_varsayilan_olarak_kapalidir_ve_mevcut_esigi_korur():
    policy = dogrulanmis_esik_politikasi_olustur((validation(),))
    assert policy.enabled is False
    assert policy.minimum_momentum_score("E3") == 10


def test_acik_politika_dogrulanmis_esigi_uygular():
    policy = dogrulanmis_esik_politikasi_olustur((validation(),), enabled=True)
    assert policy.enabled is True
    assert policy.minimum_momentum_score("E3") == 15


def test_dogrulanmayan_satir_politikaya_alinmaz():
    policy = dogrulanmis_esik_politikasi_olustur(
        (validation(verdict="Üstünlük doğrulanmadı"),), enabled=True
    )
    assert policy.enabled is False
    assert dict(policy.stage_minimum_momentum_scores) == {}


def test_e3_adayi_yeni_momentum_esiginin_altinda_e1e_indirilir():
    policy = PreBreakoutThresholdPolicy(
        enabled=True, stage_minimum_momentum_scores={"E3": 15}
    )
    result = asamayi_belirle(
        75, features(), late_entry=False, momentum_score=14,
        threshold_policy=policy,
    )
    assert result is PreBreakoutStage.E1


def test_e3_adayi_yeni_momentum_esigini_gecerse_e3_kalir():
    policy = PreBreakoutThresholdPolicy(
        enabled=True, stage_minimum_momentum_scores={"E3": 15}
    )
    result = asamayi_belirle(
        75, features(), late_entry=False, momentum_score=15,
        threshold_policy=policy,
    )
    assert result is PreBreakoutStage.E3


def test_politika_degerleri_dogrulanir():
    with pytest.raises(ValueError):
        PreBreakoutThresholdPolicy(enabled=True, stage_minimum_momentum_scores={"E1": 12})
    with pytest.raises(ValueError):
        PreBreakoutThresholdPolicy(enabled=True, stage_minimum_momentum_scores={"E3": 21})
