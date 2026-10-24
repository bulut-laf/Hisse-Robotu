from __future__ import annotations

import time

from backend.app.funds.fund_profile_nonblocking_refresh import (
    _reset_for_tests,
    queue_selected_fund_auto_refresh,
)


def setup_function() -> None:
    _reset_for_tests()


def test_first_call_returns_without_waiting_for_loader() -> None:
    def loader():
        time.sleep(0.25)
        return "ok"

    started = time.perf_counter()
    state = queue_selected_fund_auto_refresh("AAA", loader=loader, timeout_seconds=2.0)
    elapsed = time.perf_counter() - started
    assert state.status == "RUNNING"
    assert elapsed < 0.10


def test_completed_result_is_collected_on_later_render() -> None:
    queue_selected_fund_auto_refresh("BBB", loader=lambda: "done", timeout_seconds=2.0)
    deadline = time.time() + 1.0
    state = None
    while time.time() < deadline:
        state = queue_selected_fund_auto_refresh("BBB", loader=lambda: "unused", timeout_seconds=2.0)
        if state.status == "DONE":
            break
        time.sleep(0.01)
    assert state is not None
    assert state.status == "DONE"
    assert state.result == "done"


def test_failure_isolated_from_caller() -> None:
    def loader():
        raise RuntimeError("network-down")

    queue_selected_fund_auto_refresh("CCC", loader=loader, timeout_seconds=2.0)
    deadline = time.time() + 1.0
    state = None
    while time.time() < deadline:
        state = queue_selected_fund_auto_refresh("CCC", loader=lambda: "unused", timeout_seconds=2.0)
        if state.status == "FAILED":
            break
        time.sleep(0.01)
    assert state is not None
    assert state.status == "FAILED"
    assert "network-down" in (state.error or "")


def test_timeout_is_bounded() -> None:
    def loader():
        time.sleep(0.20)
        return "late"

    queue_selected_fund_auto_refresh("DDD", loader=loader, timeout_seconds=0.02)
    time.sleep(0.04)
    state = queue_selected_fund_auto_refresh("DDD", loader=lambda: "unused", timeout_seconds=0.02)
    assert state.status == "TIMEOUT"
