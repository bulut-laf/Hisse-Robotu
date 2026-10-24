from types import SimpleNamespace

from backend.app.analysis.daily_operation_panel import DailyOperationSummary
from backend.app.analysis.morning_operation_snapshot import (
    build_morning_operation_snapshot,
)


def _summary(*, locked=False, alerts=()):
    return DailyOperationSummary(
        delayed_data_status="OK",
        delayed_data_age_minutes=5.0,
        delayed_data_locked=locked,
        pending_signal_horizons=0,
        completed_signal_horizons=0,
        signal_record_count=0,
        trade_record_count=0,
        shadow_trade_count=0,
        real_trade_count=0,
        alerts=tuple(alerts),
        tasks=(),
    )


def _candidate(symbol):
    return SimpleNamespace(
        sembol=symbol,
        hacim_orani=1.7,
        sinyal=SimpleNamespace(
            skor=81,
            karar="Pozitif Teknik Görünüm",
            pozitif_nedenler=("Momentum güçlü.",),
            riskler=("Stop disiplini gerekli.",),
        ),
        risk_plani=SimpleNamespace(risk_odul_orani=2.2),
    )


def test_morning_operation_snapshot_keeps_candidates_when_data_lock_is_active():
    result = build_morning_operation_snapshot(
        operation_summary=_summary(locked=True),
        scan_result=SimpleNamespace(adaylar=(_candidate("TUPRS.IS"),)),
    )

    assert result.operation_state == "UYARILI_HAZIR"
    assert result.candidate_count == 1
    assert result.candidates[0].symbol == "TUPRS"


def test_morning_operation_snapshot_keeps_candidates_on_critical_alert():
    alert = SimpleNamespace(level="Kritik")
    result = build_morning_operation_snapshot(
        operation_summary=_summary(alerts=(alert,)),
        scan_result=SimpleNamespace(adaylar=(_candidate("TUPRS.IS"),)),
    )

    assert result.operation_state == "UYARILI_HAZIR"
    assert result.candidate_count == 1
    assert result.candidates[0].symbol == "TUPRS"


def test_morning_operation_snapshot_exposes_up_to_five_candidates_when_ready():
    scan = SimpleNamespace(
        adaylar=tuple(_candidate(f"S{i}.IS") for i in range(1, 8))
    )

    result = build_morning_operation_snapshot(
        operation_summary=_summary(),
        scan_result=scan,
    )

    assert result.operation_state == "HAZIR"
    assert result.candidate_count == 5
    assert [item.symbol for item in result.candidates] == [
        "S1", "S2", "S3", "S4", "S5"
    ]
