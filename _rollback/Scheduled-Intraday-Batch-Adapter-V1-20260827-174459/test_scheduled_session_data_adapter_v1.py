from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from backend.app.data.delayed_data_pilot import DelayedDataSnapshot
from backend.app.operations.scheduled_session_data_adapter import (
    POSTOPEN,
    PRECLOSE,
    PREOPEN,
    ScheduledSessionDataAdapterError,
    build_scheduled_session_data_evidence,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")


def snapshot(
    *,
    when: datetime,
    locked: bool = False,
    preview_only: bool = True,
    day_open: float = 102.0,
    last_price: float = 104.0,
) -> DelayedDataSnapshot:
    return DelayedDataSnapshot(
        symbol="THYAO.IS",
        exchange_time=when,
        received_time=when,
        measured_delay_minutes=15.0,
        expected_delay_minutes=15,
        status="Gün içi ön izleme",
        locked=locked,
        preview_only=preview_only,
        last_price=last_price,
        day_open=day_open,
        day_high=max(day_open, last_price) + 1.0,
        day_low=min(day_open, last_price) - 1.0,
        cumulative_volume=1_000_000.0,
        latest_bar_volume=50_000.0,
        latest_bar_completed=False,
        missing_bar_count=0,
    )


def test_preopen_is_context_only_and_does_not_call_provider():
    calls = []

    def fetcher(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("PREOPEN must not call intraday provider")

    result = build_scheduled_session_data_evidence(
        "THYAO",
        phase=PREOPEN,
        now=datetime(2026, 8, 28, 8, 45, tzinfo=ISTANBUL),
        fetcher=fetcher,
    )

    assert result.phase == "PREOPEN"
    assert result.source_status == "PREOPEN_CONTEXT_ONLY"
    assert result.intraday_required is False
    assert result.gap_ready is False
    assert result.al_sat_decision_allowed is False
    assert calls == []


def test_postopen_before_1005_is_blocked_without_provider_call():
    calls = []

    def fetcher(*args, **kwargs):
        calls.append(1)
        raise AssertionError("too-early POSTOPEN must not fetch")

    result = build_scheduled_session_data_evidence(
        "THYAO",
        phase=POSTOPEN,
        now=datetime(2026, 8, 28, 10, 4, tzinfo=ISTANBUL),
        fetcher=fetcher,
    )

    assert result.source_status == "POSTOPEN_TOO_EARLY"
    assert result.intraday_usable is False
    assert calls == []


def test_postopen_1005_computes_real_day_open_gap_from_prior_close():
    now = datetime(2026, 8, 28, 10, 5, tzinfo=ISTANBUL)

    def fetcher(symbol, *, config, now):
        return snapshot(when=now, day_open=102.0, last_price=104.0)

    result = build_scheduled_session_data_evidence(
        "THYAO",
        phase=POSTOPEN,
        prior_close=100.0,
        now=now,
        fetcher=fetcher,
    )

    assert result.intraday_usable is True
    assert result.gap_ready is True
    assert result.gap_percent == 2.0
    assert result.move_from_open_percent == pytest.approx(1.9608)
    assert result.reason == "POSTOPEN_GAP_ENTRY_EVIDENCE_READY"
    assert result.canonical_write_allowed is False
    assert result.ranking_write_allowed is False
    assert result.profile_write_allowed is False
    assert result.al_sat_decision_allowed is False


def test_postopen_without_prior_close_does_not_invent_gap():
    now = datetime(2026, 8, 28, 10, 10, tzinfo=ISTANBUL)

    def fetcher(symbol, *, config, now):
        return snapshot(when=now)

    result = build_scheduled_session_data_evidence(
        "THYAO",
        phase=POSTOPEN,
        now=now,
        fetcher=fetcher,
    )

    assert result.intraday_usable is True
    assert result.gap_ready is False
    assert result.gap_percent is None
    assert result.reason == "POSTOPEN_EVIDENCE_READY_PRIOR_CLOSE_REQUIRED_FOR_GAP"


def test_preclose_1720_is_read_only_preview():
    now = datetime(2026, 8, 28, 17, 20, tzinfo=ISTANBUL)

    def fetcher(symbol, *, config, now):
        return snapshot(when=now)

    result = build_scheduled_session_data_evidence(
        "THYAO",
        phase=PRECLOSE,
        now=now,
        fetcher=fetcher,
    )

    assert result.intraday_usable is True
    assert result.preview_only is True
    assert result.reason == "PRECLOSE_READ_ONLY_PREVIEW"
    assert result.canonical_write_allowed is False
    assert result.al_sat_decision_allowed is False


def test_preclose_after_1830_is_closed_without_provider_call():
    calls = []

    def fetcher(*args, **kwargs):
        calls.append(1)
        raise AssertionError("closed PRE-CLOSE window must not fetch")

    result = build_scheduled_session_data_evidence(
        "THYAO",
        phase=PRECLOSE,
        now=datetime(2026, 8, 28, 18, 30, tzinfo=ISTANBUL),
        fetcher=fetcher,
    )

    assert result.source_status == "PRECLOSE_WINDOW_CLOSED"
    assert result.intraday_usable is False
    assert calls == []


def test_locked_intraday_snapshot_fails_closed():
    now = datetime(2026, 8, 28, 17, 25, tzinfo=ISTANBUL)

    def fetcher(symbol, *, config, now):
        return snapshot(when=now, locked=True)

    result = build_scheduled_session_data_evidence(
        "THYAO",
        phase=PRECLOSE,
        now=now,
        fetcher=fetcher,
    )

    assert result.intraday_usable is False
    assert result.locked is True
    assert result.reason == "INTRADAY_SOURCE_LOCKED"


def test_invalid_phase_is_rejected():
    with pytest.raises(ScheduledSessionDataAdapterError):
        build_scheduled_session_data_evidence(
            "THYAO",
            phase="UNKNOWN",
            now=datetime(2026, 8, 28, 12, 0, tzinfo=ISTANBUL),
        )