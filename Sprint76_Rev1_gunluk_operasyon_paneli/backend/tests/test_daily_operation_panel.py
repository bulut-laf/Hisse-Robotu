from __future__ import annotations

from datetime import date

from backend.app.analysis.daily_operation_panel import (
    build_daily_operation_summary,
    alert_rows,
    task_rows,
)
from backend.app.analysis.signal_outcome_tracking import (
    HorizonOutcome,
    SignalOutcome,
    SignalSnapshot,
)
from backend.app.data.delayed_data_pilot import PilotLogRecord


def pilot(*, locked=False, missing=0, preview=True):
    return PilotLogRecord(
        symbol="THYAO.IS",
        source="yfinance",
        exchange_time="2026-07-31T14:00:00+03:00",
        received_time="2026-07-31T14:15:00+03:00",
        measured_delay_minutes=15.0,
        expected_delay_minutes=15,
        status=(
            "Eski veri — Analiz kilitli"
            if locked
            else "Gün içi ön izleme"
        ),
        locked=locked,
        preview_only=preview,
        last_price=100.0,
        cumulative_volume=1000000.0,
        latest_bar_volume=10000.0,
        latest_bar_completed=False,
        missing_bar_count=missing,
        price_change_percent=1.0,
        error_message="",
    )


def signal(*, available=False):
    snapshot = SignalSnapshot(
        symbol="THYAO",
        signal_date=date(2026, 7, 1),
        reference_price=100.0,
        decision_class="İzlemeye Değer",
        quality_score=75,
        daily_direction="Pozitif",
        weekly_direction="Pozitif",
    )
    horizons = tuple(
        HorizonOutcome(
            horizon=horizon,
            available=available,
            end_date=date(2026, 7, 31) if available else None,
            close_return_percent=2.0 if available else None,
            maximum_favorable_excursion_percent=4.0 if available else None,
            maximum_adverse_excursion_percent=-1.0 if available else None,
            target_1_hit=False if available else None,
            target_2_hit=False if available else None,
            stop_hit=False if available else None,
        )
        for horizon in (5, 10, 20)
    )
    return SignalOutcome(
        snapshot=snapshot,
        horizons=horizons,
        evaluated_at="2026-07-31T14:15:00+03:00",
    )


def test_veri_olcumu_yoksa_kritik_uyari_ve_gorev_uretilir():
    result = build_daily_operation_summary(
        pilot_records=(),
        signal_outcomes=(),
        trade_records=(),
    )

    assert result.delayed_data_locked
    assert any(
        item.title == "Gecikmeli veri ölçümü yok"
        for item in result.alerts
    )
    assert any(
        item.target_module == "Gecikmeli Veri Pilotu"
        for item in result.tasks
    )


def test_bekleyen_5_10_20_sonuclari_sayilir():
    result = build_daily_operation_summary(
        pilot_records=(pilot(),),
        signal_outcomes=(signal(available=False),),
        trade_records=(),
    )

    assert result.pending_signal_horizons == 3
    assert result.completed_signal_horizons == 0
    assert any(
        item.title == "Bekleyen sonuç ölçümleri"
        for item in result.alerts
    )


def test_tamamlanan_sonuclar_sayilir():
    result = build_daily_operation_summary(
        pilot_records=(pilot(),),
        signal_outcomes=(signal(available=True),),
        trade_records=(),
    )

    assert result.completed_signal_horizons == 3
    assert result.pending_signal_horizons == 0


def test_veri_kilidi_en_yuksek_oncelikli_uyaridir():
    result = build_daily_operation_summary(
        pilot_records=(pilot(locked=True),),
        signal_outcomes=(),
        trade_records=(),
    )

    assert result.alerts[0].priority == 1
    assert result.alerts[0].title == "Veri güvenlik kilidi aktif"


def test_eksik_bar_uyarisi_uretilir():
    result = build_daily_operation_summary(
        pilot_records=(pilot(missing=2),),
        signal_outcomes=(),
        trade_records=(),
    )

    assert any("Eksik gün içi bar" == item.title for item in result.alerts)


def test_tablo_satirlari_uretilir():
    result = build_daily_operation_summary(
        pilot_records=(pilot(),),
        signal_outcomes=(),
        trade_records=(),
    )

    assert alert_rows(result.alerts)
    assert task_rows(result.tasks)
    assert "İlgili ekran" in task_rows(result.tasks)[0]
