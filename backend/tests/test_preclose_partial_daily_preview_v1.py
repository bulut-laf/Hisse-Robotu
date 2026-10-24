from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from backend.app.data.batch_market_data import (
    BatchMarketDataFailure,
    BatchMarketDataResult,
)
from backend.app.data.delayed_data_pilot import DelayedDataSnapshot
from backend.app.operations.preclose_partial_daily_preview import (
    PreclosePartialDailyPreviewError,
    build_preclose_overlay_fetcher,
    overlay_partial_daily_bar,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")


def _daily() -> pd.DataFrame:
    idx = pd.to_datetime(["2026-08-25", "2026-08-26"])
    return pd.DataFrame(
        {
            "Open": [98.0, 99.0],
            "High": [101.0, 102.0],
            "Low": [97.0, 98.0],
            "Close": [100.0, 101.0],
            "Volume": [900_000.0, 1_000_000.0],
        },
        index=idx,
    )


def _snapshot(
    when: datetime,
    *,
    symbol: str = "THYAO.IS",
    locked: bool = False,
) -> DelayedDataSnapshot:
    return DelayedDataSnapshot(
        symbol=symbol,
        exchange_time=when,
        received_time=when,
        measured_delay_minutes=15.0,
        expected_delay_minutes=15,
        status="Gün içi ön izleme",
        locked=locked,
        preview_only=True,
        last_price=104.0,
        day_open=102.0,
        day_high=105.0,
        day_low=101.0,
        cumulative_volume=2_000_000.0,
        latest_bar_volume=100_000.0,
        latest_bar_completed=False,
        missing_bar_count=0,
    )


def test_partial_daily_bar_is_appended_for_today():
    now = datetime(2026, 8, 27, 17, 20, tzinfo=ISTANBUL)
    out = overlay_partial_daily_bar(
        _daily(),
        _snapshot(now),
        observed_at=now,
    )

    assert list(pd.to_datetime(out.index).date)[-1].isoformat() == "2026-08-27"
    assert float(out.iloc[-1]["Open"]) == 102.0
    assert float(out.iloc[-1]["High"]) == 105.0
    assert float(out.iloc[-1]["Low"]) == 101.0
    assert float(out.iloc[-1]["Close"]) == 104.0
    assert float(out.iloc[-1]["Volume"]) == 2_000_000.0


def test_existing_today_row_is_replaced_not_duplicated():
    now = datetime(2026, 8, 27, 17, 25, tzinfo=ISTANBUL)
    base = _daily()
    base.loc[pd.Timestamp("2026-08-27")] = [1, 1, 1, 1, 1]

    out = overlay_partial_daily_bar(
        base,
        _snapshot(now),
        observed_at=now,
    )

    dates = list(pd.to_datetime(out.index).date)
    assert dates.count(now.date()) == 1
    assert float(out.loc[pd.Timestamp("2026-08-27"), "Close"]) == 104.0


def test_locked_snapshot_fails_closed():
    now = datetime(2026, 8, 27, 17, 20, tzinfo=ISTANBUL)
    with pytest.raises(PreclosePartialDailyPreviewError, match="kilidi"):
        overlay_partial_daily_bar(
            _daily(),
            _snapshot(now, locked=True),
            observed_at=now,
        )


def test_preclose_window_ends_at_1830():
    now = datetime(2026, 8, 27, 18, 30, tzinfo=ISTANBUL)
    with pytest.raises(PreclosePartialDailyPreviewError, match="canonical close"):
        overlay_partial_daily_bar(
            _daily(),
            _snapshot(now),
            observed_at=now,
        )


def test_overlay_fetcher_reuses_canonical_daily_and_intraday_batch():
    now = datetime(2026, 8, 27, 17, 20, tzinfo=ISTANBUL)
    calls = []

    def daily_fetcher(symbols, *, islem_gunu, indirme_donemi, **kwargs):
        calls.append(("daily", tuple(symbols), islem_gunu, indirme_donemi))
        return BatchMarketDataResult(
            veriler={"THYAO.IS": _daily()},
            hatalar=(),
        )

    def intraday_fetcher(symbols, *, now):
        calls.append(("intraday", tuple(symbols), now.hour, now.minute))
        return SimpleNamespace(
            snapshots={"THYAO.IS": _snapshot(now)},
            failures=(),
        )

    fetch = build_preclose_overlay_fetcher(
        now=now,
        daily_fetcher=daily_fetcher,
        intraday_fetcher=intraday_fetcher,
    )
    out = fetch(
        ("THYAO.IS",),
        islem_gunu=160,
        indirme_donemi="1y",
    )

    assert calls[0][:2] == ("daily", ("THYAO.IS",))
    assert calls[1][:2] == ("intraday", ("THYAO.IS",))
    assert "THYAO.IS" in out.veriler
    assert pd.Timestamp(out.veriler["THYAO.IS"].index[-1]).date() == now.date()


def test_missing_intraday_symbol_is_excluded_and_failure_is_visible():
    now = datetime(2026, 8, 27, 17, 20, tzinfo=ISTANBUL)

    def daily_fetcher(symbols, *, islem_gunu, indirme_donemi, **kwargs):
        return BatchMarketDataResult(
            veriler={"THYAO.IS": _daily()},
            hatalar=(),
        )

    def intraday_fetcher(symbols, *, now):
        return SimpleNamespace(
            snapshots={},
            failures=(
                SimpleNamespace(
                    symbol="THYAO.IS",
                    error="no current partial",
                ),
            ),
        )

    fetch = build_preclose_overlay_fetcher(
        now=now,
        daily_fetcher=daily_fetcher,
        intraday_fetcher=intraday_fetcher,
    )
    out = fetch(("THYAO.IS",))

    assert out.veriler == {}
    assert len(out.hatalar) == 1
    assert out.hatalar[0].sembol == "THYAO.IS"
    assert "PRECLOSE_INTRADAY_MISSING" in out.hatalar[0].hata


def test_module_has_no_canonical_persistence_authority():
    import inspect
    import backend.app.operations.preclose_partial_daily_preview as module

    source = inspect.getsource(module)
    forbidden = (
        "RankObservationJsonlStore",
        "ResearchProfileMemory",
        "DecisionOutputArchiveJsonStore",
        "ScheduledRunJsonStore",
        "append_profile",
        "append_observation",
    )
    assert all(token not in source for token in forbidden)