from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.app.analysis.signal_outcome_tracking import (
    HorizonOutcome,
    SignalOutcome,
    SignalSnapshot,
)
from backend.app.analysis.walk_forward_calibration import (
    CalibrationParameters,
    WalkForwardCalibrationError,
    aggregate_rows,
    calibration_to_csv,
    run_walk_forward_calibration,
    window_rows,
)


def outcome(
    index: int,
    *,
    positive: bool,
) -> SignalOutcome:
    signal_date = date(2025, 1, 1) + timedelta(days=index)
    snapshot = SignalSnapshot(
        symbol=f"TST{index}",
        signal_date=signal_date,
        reference_price=100.0,
        decision_class=(
            "İzlemeye Değer" if positive else "Temkinli İzle"
        ),
        quality_score=80 if positive else 50,
        daily_direction="Pozitif" if positive else "Negatif",
        weekly_direction="Pozitif" if positive else "Negatif",
        divergence_type=(
            "Normal Pozitif" if positive else "Normal Negatif"
        ),
        market_regime="Olumlu" if positive else "Olumsuz",
        momentum_state="Pozitif" if positive else "Negatif",
        volume_confirmation=positive,
        atr_percent=2.5 if positive else 6.0,
        risk_reward_ratio=2.5 if positive else 1.2,
    )
    value = 4.0 if positive else -3.0
    horizons = tuple(
        HorizonOutcome(
            horizon=horizon,
            available=True,
            end_date=signal_date + timedelta(days=horizon),
            close_return_percent=value,
            maximum_favorable_excursion_percent=6.0 if positive else 1.0,
            maximum_adverse_excursion_percent=-1.0 if positive else -5.0,
            target_1_hit=positive,
            target_2_hit=False,
            stop_hit=not positive,
        )
        for horizon in (5, 10, 20)
    )
    return SignalOutcome(
        snapshot=snapshot,
        horizons=horizons,
        evaluated_at="2026-01-01T00:00:00+00:00",
    )


def dataset():
    records = []
    for index in range(90):
        positive = index % 3 != 0
        records.append(outcome(index, positive=positive))
    return tuple(records)


def small_grid():
    return (
        CalibrationParameters(
            minimum_quality_score=70,
            minimum_risk_reward=2.0,
            minimum_atr_percent=1.0,
            maximum_atr_percent=4.5,
            require_positive_daily_trend=True,
            require_positive_weekly_trend=True,
            require_positive_momentum=True,
            require_volume_confirmation=True,
            require_positive_divergence=True,
        ),
        CalibrationParameters(
            minimum_quality_score=50,
            minimum_risk_reward=1.0,
            minimum_atr_percent=0.5,
            maximum_atr_percent=7.0,
            require_positive_daily_trend=False,
            require_positive_weekly_trend=False,
            require_positive_momentum=False,
            require_volume_confirmation=False,
            require_positive_divergence=False,
        ),
    )


def test_egitim_ve_dogrulama_donemleri_zamansal_olarak_ayridir():
    result = run_walk_forward_calibration(
        dataset(),
        horizon=10,
        training_size=30,
        validation_size=15,
        step_size=15,
        minimum_training_samples=5,
        minimum_validation_samples=3,
        parameter_grid=small_grid(),
    )

    assert result.windows
    assert all(
        item.training_end < item.validation_start
        for item in result.windows
    )


def test_5_10_20_gunluk_ufuklar_ayri_calistirilabilir():
    for horizon in (5, 10, 20):
        result = run_walk_forward_calibration(
            dataset(),
            horizon=horizon,
            training_size=30,
            validation_size=15,
            step_size=15,
            minimum_training_samples=5,
            minimum_validation_samples=3,
            parameter_grid=small_grid(),
        )
        assert result.horizon == horizon


def test_dogrulama_basarisi_olmayan_pencere_reddedilir():
    records = tuple(
        outcome(index, positive=index < 45)
        for index in range(60)
    )
    result = run_walk_forward_calibration(
        records,
        horizon=10,
        training_size=30,
        validation_size=15,
        step_size=15,
        minimum_training_samples=5,
        minimum_validation_samples=3,
        parameter_grid=small_grid(),
    )

    assert any(not item.accepted for item in result.windows)


def test_minimum_ornek_kilidi_uygulanir():
    with pytest.raises(
        WalkForwardCalibrationError,
        match="yeterli tamamlanmış kayıt",
    ):
        run_walk_forward_calibration(
            dataset()[:20],
            horizon=10,
            training_size=15,
            validation_size=10,
            parameter_grid=small_grid(),
        )


def test_kararli_parametre_bolgesi_raporlanir():
    result = run_walk_forward_calibration(
        dataset(),
        horizon=10,
        training_size=30,
        validation_size=15,
        step_size=15,
        minimum_training_samples=5,
        minimum_validation_samples=3,
        parameter_grid=small_grid(),
    )

    assert result.aggregates
    assert all(0 <= item.stability_score <= 100 for item in result.aggregates)
    assert all(
        item.status in {
            "Kararlı bölge",
            "İzlenebilir",
            "Aşırı uyum riski",
        }
        for item in result.aggregates
    )


def test_tablo_ve_csv_raporu_uretilir():
    result = run_walk_forward_calibration(
        dataset(),
        horizon=20,
        training_size=30,
        validation_size=15,
        step_size=15,
        minimum_training_samples=5,
        minimum_validation_samples=3,
        parameter_grid=small_grid(),
    )

    assert window_rows(result)
    assert aggregate_rows(result)
    assert calibration_to_csv(result).startswith(b"\xef\xbb\xbf")


def test_walk_forward_gelecek_performansi_garanti_etmez():
    result = run_walk_forward_calibration(
        dataset(),
        horizon=10,
        training_size=30,
        validation_size=15,
        step_size=15,
        minimum_training_samples=5,
        minimum_validation_samples=3,
        parameter_grid=small_grid(),
    )

    assert "gelecek performansı garanti etmez" in result.warning
