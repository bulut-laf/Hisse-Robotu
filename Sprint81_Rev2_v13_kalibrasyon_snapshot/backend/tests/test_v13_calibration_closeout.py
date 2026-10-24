from __future__ import annotations

from datetime import date

from backend.app.analysis.shadow_portfolio import ShadowPosition
from backend.app.analysis.signal_outcome_tracking import (
    HorizonOutcome,
    SignalOutcome,
    SignalSnapshot,
)
from backend.app.analysis.success_comparison_report import (
    build_success_comparison_report,
)
from backend.app.analysis.v13_calibration_closeout import (
    DEVAM,
    KALIBRASYON_GEREKLI,
    TEMKINLI_DEVAM,
    build_v13_calibration_decision,
    criterion_rows,
    decision_summary_rows,
)
from backend.app.data.delayed_data_pilot import PilotLogRecord


def pilot(index: int, *, locked: bool = False) -> PilotLogRecord:
    return PilotLogRecord(
        symbol="THYAO.IS",
        source="yfinance",
        exchange_time=f"2026-07-31T14:{index:02d}:00+03:00",
        received_time=f"2026-07-31T14:{index + 15:02d}:00+03:00",
        measured_delay_minutes=15.0,
        expected_delay_minutes=15,
        status="Gün içi ön izleme",
        locked=locked,
        preview_only=True,
        last_price=100.0,
        cumulative_volume=100000.0,
        latest_bar_volume=10000.0,
        latest_bar_completed=False,
        missing_bar_count=0,
        price_change_percent=1.0,
        error_message="",
    )


def outcome(symbol: str, return_percent: float) -> SignalOutcome:
    snapshot = SignalSnapshot(
        symbol=symbol,
        signal_date=date(2026, 7, 1),
        reference_price=100.0,
        decision_class="İzlemeye Değer",
        quality_score=80,
        daily_direction="Pozitif",
        weekly_direction="Pozitif",
        market_regime="Pozitif",
        sector="Banka",
        momentum_state="Pozitif MACD",
        volume_confirmation=True,
    )
    horizons = tuple(
        HorizonOutcome(
            horizon=horizon,
            available=True,
            end_date=date(2026, 7, horizon),
            close_return_percent=return_percent,
            maximum_favorable_excursion_percent=return_percent + 2,
            maximum_adverse_excursion_percent=-1.0,
            target_1_hit=True,
            target_2_hit=return_percent > 5,
            stop_hit=False,
        )
        for horizon in (5, 10, 20)
    )
    return SignalOutcome(
        snapshot=snapshot,
        horizons=horizons,
        evaluated_at="2026-07-31T12:00:00+00:00",
    )


def closed_position(index: int) -> ShadowPosition:
    return ShadowPosition(
        symbol=f"SYM{index}",
        entry_date=date(2026, 7, 1),
        entry_price=100.0,
        quantity=10,
        capital_at_entry=10000.0,
        status="Kapalı",
        exit_date=date(2026, 7, 15),
        exit_price=105.0,
        close_reason="Test",
    )


def test_tum_esikler_gecilince_devam_karari_uretilir():
    outcomes = tuple(outcome(f"SYM{i}", 4.0) for i in range(5))
    report = build_success_comparison_report(
        outcomes,
        minimum_sample_size=5,
    )

    decision = build_v13_calibration_decision(
        pilot_records=tuple(pilot(i) for i in range(5)),
        signal_outcomes=outcomes,
        shadow_positions=tuple(closed_position(i) for i in range(5)),
        comparison_report=report,
        minimum_sufficient_comparisons=3,
    )

    assert decision.decision == DEVAM
    assert decision.failed_critical_count == 0
    assert decision.warning_count == 0


def test_kritik_veri_eksiginde_kalibrasyon_gerekli_karari_uretilir():
    report = build_success_comparison_report(
        (),
        minimum_sample_size=5,
    )

    decision = build_v13_calibration_decision(
        pilot_records=(),
        signal_outcomes=(),
        shadow_positions=(),
        comparison_report=report,
    )

    assert decision.decision == KALIBRASYON_GEREKLI
    assert decision.failed_critical_count > 0


def test_kritik_zincirler_gecerli_ama_orneklem_azsa_temkinli_devam():
    outcomes = tuple(outcome(f"SYM{i}", 4.0) for i in range(5))
    report = build_success_comparison_report(
        outcomes,
        minimum_sample_size=5,
    )

    decision = build_v13_calibration_decision(
        pilot_records=tuple(pilot(i) for i in range(5)),
        signal_outcomes=outcomes,
        shadow_positions=(),
        comparison_report=report,
        minimum_sufficient_comparisons=999,
    )

    assert decision.decision == TEMKINLI_DEVAM
    assert decision.failed_critical_count == 0
    assert decision.warning_count > 0


def test_kapanis_tablolari_uretilir():
    outcomes = tuple(outcome(f"SYM{i}", 4.0) for i in range(5))
    report = build_success_comparison_report(
        outcomes,
        minimum_sample_size=5,
    )
    decision = build_v13_calibration_decision(
        pilot_records=tuple(pilot(i) for i in range(5)),
        signal_outcomes=outcomes,
        shadow_positions=tuple(closed_position(i) for i in range(5)),
        comparison_report=report,
    )

    assert criterion_rows(decision)
    assert decision_summary_rows(decision)
    assert decision_summary_rows(decision)[0]["Metrik"] == "Kalibrasyon kararı"
