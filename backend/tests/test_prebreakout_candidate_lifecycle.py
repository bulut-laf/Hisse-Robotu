from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

from backend.app.prebreakout.prebreakout_candidate_lifecycle import (
    CandidateLifecycleConfig,
    CandidateLifecycleStatus,
    CandidatePriceObservation,
    adayin_yasam_dongusunu_degerlendir,
    yeni_sinyal_tekrar_mi,
    yasam_dongusu_kaydet,
    yasam_dongusu_ozeti,
    yasam_dongusu_yukle,
)
from backend.app.prebreakout.prebreakout_live_watch import PreBreakoutLiveSignal


def _signal(*, signal_date: str = "2026-08-01", stage: str = "E3") -> PreBreakoutLiveSignal:
    return PreBreakoutLiveSignal(
        schema_version=1,
        signal_id=f"TUPRS-{signal_date}-{stage}",
        symbol="TUPRS.IS",
        signal_date=signal_date,
        recorded_at_utc=f"{signal_date}T08:00:00Z",
        stage=stage,
        stage_label="Tetiklenmeye yakın",
        score=78,
        accepted=True,
        close=100.0,
        minimum_momentum_score=12,
        threshold_policy_enabled=True,
        threshold_policy_source="test",
        features={},
        reasons=(),
        risks=(),
        payload_sha256="test",
    )


def _obs(day: int, *, high: float, low: float, close: float) -> CandidatePriceObservation:
    return CandidatePriceObservation(date(2026, 8, day), high, low, close)


def test_tetiklenme_ilk_olustugu_gunde_kaydedilir() -> None:
    record = adayin_yasam_dongusunu_degerlendir(
        _signal(),
        [_obs(2, high=101, low=99, close=100), _obs(3, high=104, low=100, close=103)],
    )
    assert record.status is CandidateLifecycleStatus.TETIKLENDI
    assert record.status_date == "2026-08-03"
    assert record.observed_session_count == 2


def test_ayni_barda_risk_once_degerlendirilir() -> None:
    record = adayin_yasam_dongusunu_degerlendir(
        _signal(),
        [_obs(2, high=104, low=94, close=100)],
    )
    assert record.status is CandidateLifecycleStatus.BASARISIZ


def test_sure_dolunca_acik_aday_kapanir() -> None:
    observations = [_obs(day, high=102, low=98, close=100) for day in range(2, 6)]
    record = adayin_yasam_dongusunu_degerlendir(
        _signal(),
        observations,
        config=CandidateLifecycleConfig(expiry_observation_count=4),
    )
    assert record.status is CandidateLifecycleStatus.SURESI_DOLDU
    assert record.observed_session_count == 4


def test_yetersiz_gozlemde_hazirlik_devam_eder() -> None:
    record = adayin_yasam_dongusunu_degerlendir(
        _signal(),
        [_obs(2, high=101, low=99, close=100)],
        as_of_date=date(2026, 8, 4),
    )
    assert record.status is CandidateLifecycleStatus.HAZIRLIK
    assert record.elapsed_calendar_days == 3


def test_ayni_hisse_bekleme_suresinde_tekrar_aday_olmaz() -> None:
    assert yeni_sinyal_tekrar_mi(
        [_signal()], symbol="TUPRS.IS", signal_date=date(2026, 8, 5), cooldown_days=5
    )
    assert not yeni_sinyal_tekrar_mi(
        [_signal()], symbol="TUPRS.IS", signal_date=date(2026, 8, 7), cooldown_days=5
    )


def test_yasam_dongusu_kayitlari_yuvarlak_geciste_korunur(tmp_path: Path) -> None:
    record = adayin_yasam_dongusunu_degerlendir(
        _signal(), [_obs(2, high=104, low=99, close=103)]
    )
    target = tmp_path / "lifecycle.json"
    yasam_dongusu_kaydet([record], target)
    loaded = yasam_dongusu_yukle(target)
    assert loaded == (record,)
    assert yasam_dongusu_ozeti(loaded)["TETIKLENDI"] == 1
