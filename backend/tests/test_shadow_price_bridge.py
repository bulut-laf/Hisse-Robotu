from datetime import datetime, timezone

from backend.app.analysis.shadow_price_bridge import suggestion_from_snapshot
from backend.app.data.delayed_data_pilot import DelayedDataSnapshot


def _snapshot(*, locked: bool) -> DelayedDataSnapshot:
    stamp = datetime(2026, 8, 17, 7, 30, tzinfo=timezone.utc)
    return DelayedDataSnapshot(
        symbol="THYAO.IS",
        exchange_time=stamp,
        received_time=stamp,
        measured_delay_minutes=15.0,
        expected_delay_minutes=15,
        status="TEST",
        locked=locked,
        preview_only=True,
        last_price=321.5,
        day_open=320.0,
        day_high=322.0,
        day_low=319.0,
        cumulative_volume=1000.0,
        latest_bar_volume=100.0,
        latest_bar_completed=False,
        missing_bar_count=0,
    )


def test_unlocked_snapshot_can_prefill_manual_price():
    result = suggestion_from_snapshot(_snapshot(locked=False))
    assert result.usable is True
    assert result.price == 321.5


def test_locked_snapshot_never_prefills_manual_price():
    result = suggestion_from_snapshot(_snapshot(locked=True))
    assert result.usable is False
    assert result.price is None
