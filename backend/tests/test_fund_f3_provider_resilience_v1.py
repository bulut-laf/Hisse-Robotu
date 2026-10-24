from threading import Lock
from time import sleep

import pytest

import backend.app.funds.f3_production_population as runtime
import backend.app.funds.tefas_history_population as history_population

from backend.app.funds.store import (
    FundObservationJsonStore,
)


def universe(code):
    return {
        "fonkod": code,
    }


def history(
    code,
):
    return (
        {
            "fonKodu": code,
            "fonUnvan": "TEST",
            "kategoriDerece": 0,
            "kategoriFonSay": 29,
            "tarih": "2026-08-01",
            "fiyat": "100",
        },
        {
            "fonKodu": code,
            "fonUnvan": "TEST",
            "kategoriDerece": 0,
            "kategoriFonSay": 29,
            "tarih": "2026-08-02",
            "fiyat": "101",
        },
        {
            "fonKodu": code,
            "fonUnvan": "TEST",
            "kategoriDerece": 0,
            "kategoriFonSay": 29,
            "tarih": "2026-08-03",
            "fiyat": "102",
        },
    )


class CountingStore(
    FundObservationJsonStore
):
    def __init__(self, path):
        super().__init__(path)
        self.upsert_calls = 0

    def upsert(self, observations):
        self.upsert_calls += 1
        return super().upsert(
            observations
        )


def test_transient_reset_is_retried_then_succeeds(
    tmp_path,
    monkeypatch,
):
    store = CountingStore(
        tmp_path / "observations.json"
    )

    monkeypatch.setattr(
        runtime,
        "fetch_tefas_universe_rows",
        lambda: (
            universe("AAA"),
        ),
    )

    calls = 0

    def fake_fetch(
        code,
        **kwargs,
    ):
        nonlocal calls
        calls += 1

        if calls < 3:
            raise ConnectionResetError(
                "TEST_RESET"
            )

        return history(code)

    monkeypatch.setattr(
        history_population,
        "fetch_tefas_fund_history_rows",
        fake_fetch,
    )

    result = (
        runtime
        .populate_next_f3_production_batch(
            batch_size=1,
            worker_count=1,
            retry_attempts=3,
            retry_backoff_seconds=0,
            store=store,
        )
    )

    assert calls == 3
    assert result.succeeded_funds == (
        "AAA",
    )
    assert not result.failed_funds
    assert store.upsert_calls == 1


def test_permanent_reset_fails_after_retry_limit(
    tmp_path,
    monkeypatch,
):
    store = CountingStore(
        tmp_path / "observations.json"
    )

    monkeypatch.setattr(
        runtime,
        "fetch_tefas_universe_rows",
        lambda: (
            universe("AAA"),
        ),
    )

    calls = 0

    def fake_fetch(
        code,
        **kwargs,
    ):
        nonlocal calls
        calls += 1
        raise ConnectionResetError(
            "TEST_RESET"
        )

    monkeypatch.setattr(
        history_population,
        "fetch_tefas_fund_history_rows",
        fake_fetch,
    )

    result = (
        runtime
        .populate_next_f3_production_batch(
            batch_size=1,
            worker_count=1,
            retry_attempts=3,
            retry_backoff_seconds=0,
            store=store,
        )
    )

    assert calls == 3
    assert not result.succeeded_funds
    assert len(result.failed_funds) == 1
    assert store.upsert_calls == 0


def test_value_error_is_not_retried(
    tmp_path,
    monkeypatch,
):
    store = CountingStore(
        tmp_path / "observations.json"
    )

    monkeypatch.setattr(
        runtime,
        "fetch_tefas_universe_rows",
        lambda: (
            universe("AAA"),
        ),
    )

    calls = 0

    def fake_fetch(
        code,
        **kwargs,
    ):
        nonlocal calls
        calls += 1
        raise ValueError(
            "TEST_DATA_ERROR"
        )

    monkeypatch.setattr(
        history_population,
        "fetch_tefas_fund_history_rows",
        fake_fetch,
    )

    result = (
        runtime
        .populate_next_f3_production_batch(
            batch_size=1,
            worker_count=1,
            retry_attempts=3,
            retry_backoff_seconds=0,
            store=store,
        )
    )

    assert calls == 1
    assert len(result.failed_funds) == 1


def test_maximum_concurrency_is_two(
    tmp_path,
    monkeypatch,
):
    store = CountingStore(
        tmp_path / "observations.json"
    )

    codes = tuple(
        f"T{index:03d}"
        for index in range(10)
    )

    monkeypatch.setattr(
        runtime,
        "fetch_tefas_universe_rows",
        lambda: tuple(
            universe(code)
            for code in codes
        ),
    )

    lock = Lock()
    active = 0
    maximum = 0

    def fake_fetch(
        code,
        **kwargs,
    ):
        nonlocal active
        nonlocal maximum

        with lock:
            active += 1
            maximum = max(
                maximum,
                active,
            )

        sleep(0.01)

        with lock:
            active -= 1

        return history(code)

    monkeypatch.setattr(
        history_population,
        "fetch_tefas_fund_history_rows",
        fake_fetch,
    )

    runtime.populate_next_f3_production_batch(
        batch_size=10,
        worker_count=2,
        retry_backoff_seconds=0,
        store=store,
    )

    assert maximum <= 2
    assert maximum > 1
    assert store.upsert_calls == 1


def test_worker_three_is_rejected(
    tmp_path,
):
    store = CountingStore(
        tmp_path / "observations.json"
    )

    with pytest.raises(
        ValueError,
        match="F3_WORKER_COUNT_INVALID",
    ):
        runtime.populate_next_f3_production_batch(
            worker_count=3,
            store=store,
        )
