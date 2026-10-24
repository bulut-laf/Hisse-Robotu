from __future__ import annotations

import time

from backend.app.funds.tefas_universe_nonblocking_refresh import (
    _reset_for_tests,
    queue_tefas_universe_refresh,
)


def setup_function():
    _reset_for_tests()


def test_first_call_is_nonblocking():
    def loader():
        time.sleep(0.20)
        return "ok"

    started = time.perf_counter()
    state = queue_tefas_universe_refresh(loader=loader, timeout_seconds=2.0)
    assert state.status == "STARTED"
    assert time.perf_counter() - started < 0.10


def test_running_call_does_not_spawn_second_loader():
    calls = []

    def loader():
        calls.append(1)
        time.sleep(0.15)
        return "ok"

    queue_tefas_universe_refresh(loader=loader, timeout_seconds=2.0)
    state = queue_tefas_universe_refresh(loader=loader, timeout_seconds=2.0)
    assert state.status == "RUNNING"
    assert len(calls) == 1


def test_completed_result_is_collected():
    queue_tefas_universe_refresh(loader=lambda: "done", timeout_seconds=2.0)

    deadline = time.time() + 1.0
    while time.time() < deadline:
        state = queue_tefas_universe_refresh(loader=lambda: "unused", timeout_seconds=2.0)
        if state.status == "DONE":
            assert state.result == "done"
            return
        time.sleep(0.01)

    raise AssertionError("background TEFAS refresh did not complete")


def test_failure_is_isolated():
    def loader():
        raise RuntimeError("network down")

    queue_tefas_universe_refresh(loader=loader, timeout_seconds=2.0)

    deadline = time.time() + 1.0
    while time.time() < deadline:
        state = queue_tefas_universe_refresh(loader=lambda: "unused", timeout_seconds=2.0)
        if state.status == "FAILED":
            assert "network down" in (state.error or "")
            return
        time.sleep(0.01)

    raise AssertionError("failure was not surfaced")


def test_timeout_is_bounded():
    def loader():
        time.sleep(0.20)
        return "late"

    queue_tefas_universe_refresh(loader=loader, timeout_seconds=0.01)
    time.sleep(0.03)
    state = queue_tefas_universe_refresh(loader=lambda: "unused", timeout_seconds=0.01)
    assert state.status == "TIMEOUT"
