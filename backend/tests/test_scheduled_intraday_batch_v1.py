from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from backend.app.operations.scheduled_intraday_batch import (
    fetch_scheduled_intraday_batch,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")


def _multi_symbol_frame() -> pd.DataFrame:
    idx = pd.DatetimeIndex(
        [
            datetime(2026, 8, 28, 10, 0, tzinfo=ISTANBUL),
            datetime(2026, 8, 28, 10, 5, tzinfo=ISTANBUL),
        ]
    )
    columns = pd.MultiIndex.from_product(
        [
            ["THYAO.IS", "GARAN.IS"],
            ["Open", "High", "Low", "Close", "Volume"],
        ]
    )
    data = [
        [100, 101, 99, 100.5, 1000, 50, 51, 49, 50.5, 2000],
        [100.5, 102, 100, 101.5, 1200, 50.5, 52, 50, 51.5, 2500],
    ]
    return pd.DataFrame(data, index=idx, columns=columns)


def test_batch_download_is_one_call_for_two_symbols():
    calls = []

    def downloader(**kwargs):
        calls.append(kwargs)
        return _multi_symbol_frame()

    result = fetch_scheduled_intraday_batch(
        ["THYAO", "GARAN"],
        now=datetime(2026, 8, 28, 10, 25, tzinfo=ISTANBUL),
        chunk_size=40,
        downloader=downloader,
    )

    assert len(calls) == 1
    assert calls[0]["interval"] == "5m"
    assert calls[0]["period"] == "1d"
    assert calls[0]["threads"] is True
    assert result.requested_count == 2
    assert result.successful_count == 2
    assert result.failures == ()
    assert set(result.snapshots) == {"THYAO.IS", "GARAN.IS"}


def test_batch_snapshot_reuses_existing_delayed_pilot_fields():
    def downloader(**kwargs):
        return _multi_symbol_frame()

    result = fetch_scheduled_intraday_batch(
        ["THYAO"],
        now=datetime(2026, 8, 28, 10, 25, tzinfo=ISTANBUL),
        chunk_size=1,
        downloader=lambda **kwargs: _multi_symbol_frame().xs(
            "THYAO.IS", axis=1, level=0
        ),
    )

    item = result.snapshots["THYAO.IS"]
    assert item.day_open == 100.0
    assert item.last_price == 101.5
    assert item.cumulative_volume == 2200.0
    assert item.source == "yfinance"


def test_chunk_failure_is_fail_closed_per_symbol():
    def downloader(**kwargs):
        raise RuntimeError("offline")

    result = fetch_scheduled_intraday_batch(
        ["THYAO", "GARAN"],
        now=datetime(2026, 8, 28, 17, 20, tzinfo=ISTANBUL),
        downloader=downloader,
    )

    assert result.successful_count == 0
    assert len(result.failures) == 2
    assert {item.symbol for item in result.failures} == {"THYAO.IS", "GARAN.IS"}


def test_duplicate_symbols_are_not_downloaded_twice():
    calls = []

    def downloader(**kwargs):
        calls.append(kwargs)
        return _multi_symbol_frame().xs("THYAO.IS", axis=1, level=0)

    result = fetch_scheduled_intraday_batch(
        ["THYAO", "THYAO.IS"],
        now=datetime(2026, 8, 28, 10, 25, tzinfo=ISTANBUL),
        chunk_size=1,
        downloader=downloader,
    )

    assert result.requested_count == 1
    assert len(calls) == 1


def test_batch_adapter_has_no_persistence_or_decision_authority():
    import inspect
    import backend.app.operations.scheduled_intraday_batch as module

    source = inspect.getsource(module)
    forbidden = (
        "RankingMemory",
        "ResearchProfileMemory",
        "DecisionOutputArchiveJsonStore",
        "ScheduledRunJsonStore",
        "AL_SAT",
        "execute_scheduled_run",
    )
    assert all(token not in source for token in forbidden)