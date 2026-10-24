from pathlib import Path
import sys

root = Path(sys.argv[1])
ui = root / "backend/app/ui/fund_analysis_center.py"
helper = root / "backend/app/funds/fund_profile_nonblocking_refresh.py"
test = root / "backend/tests/test_fund_profile_nonblocking_refresh_v1.py"

text = ui.read_text(encoding="utf-8")

old_import = "from backend.app.funds.fund_auto_refresh import auto_refresh_selected_fund_if_due\n"
new_import = (
    "from backend.app.funds.fund_auto_refresh import auto_refresh_selected_fund_if_due\n"
    "from backend.app.funds.fund_profile_nonblocking_refresh import queue_selected_fund_auto_refresh\n"
)

start = text.find('    if hasattr(st, "session_state"):\n        try:\n            refresh = auto_refresh_selected_fund_if_due(')
end = text.find('    try:\n        profile = build_fund_profile_read_model(', start)

if start < 0 or end < 0:
    raise SystemExit("EXACT_BLOCK_NOT_FOUND")
if text.find('    if hasattr(st, "session_state"):\n        try:\n            refresh = auto_refresh_selected_fund_if_due(', start + 1) >= 0:
    raise SystemExit("EXACT_BLOCK_NOT_UNIQUE")
if old_import not in text:
    raise SystemExit("IMPORT_NOT_FOUND")

new_block = """    if hasattr(st, "session_state"):
        refresh_state = queue_selected_fund_auto_refresh(
            code,
            loader=lambda: auto_refresh_selected_fund_if_due(
                code,
                observation_store=fund_observation_store(),
                portfolio_store=portfolio_store,
                network_enabled=True,
            ),
            timeout_seconds=12.0,
        )
        if refresh_state.status == "RUNNING":
            st.caption("Fon verisi arka planda güncelleniyor; son kayıtlı veri gösteriliyor.")
        elif refresh_state.status == "FAILED" and hasattr(st, "warning"):
            st.warning(
                "Otomatik fon yenilemesi izole edildi; son iyi veri gösteriliyor. "
                + (refresh_state.error or "Bilinmeyen yenileme hatası")
            )
        elif refresh_state.status == "TIMEOUT" and hasattr(st, "warning"):
            st.warning("Otomatik fon yenilemesi zaman sınırını aştı; son iyi veri gösteriliyor.")
        elif refresh_state.result is not None:
            refresh = refresh_state.result
            if refresh.attempted and refresh.refreshed:
                st.caption(
                    "Otomatik güncelleme tamamlandı · "
                    f"TEFAS detay={'✓' if refresh.detail_written else '-'} · "
                    f"fiyat geçmişi={'✓' if refresh.history_written else '-'} · "
                    f"KAP portföy={'✓' if refresh.portfolio_checked else '-'} · "
                    f"FDO={'✓' if refresh.fdo_checked else '-'}"
                )
            if refresh.warnings and hasattr(st, "warning"):
                st.warning(
                    "Bazı otomatik kaynaklar izole edildi: "
                    + " | ".join(refresh.warnings[:4])
                )

"""

text = text[:start] + new_block + text[end:]
text = text.replace(old_import, new_import, 1)
ui.write_text(text, encoding="utf-8")

helper.parent.mkdir(parents=True, exist_ok=True)
helper.write_text("""from __future__ import annotations

from dataclasses import dataclass
from threading import Lock, Thread
from time import monotonic
from typing import Any, Callable

@dataclass(frozen=True)
class FundProfileRefreshState:
    status: str
    result: Any | None = None
    error: str | None = None

@dataclass
class _Job:
    started_at: float
    status: str = "RUNNING"
    result: Any | None = None
    error: str | None = None
    generation: int = 1

_LOCK = Lock()
_JOBS: dict[str, _Job] = {}

def _run(key: str, generation: int, loader: Callable[[], Any]) -> None:
    try:
        result = loader()
    except Exception as exc:
        with _LOCK:
            job = _JOBS.get(key)
            if job and job.generation == generation:
                job.status = "FAILED"
                job.error = str(exc)
        return
    with _LOCK:
        job = _JOBS.get(key)
        if job and job.generation == generation:
            job.status = "DONE"
            job.result = result

def queue_selected_fund_auto_refresh(
    fund_code: str,
    *,
    loader: Callable[[], Any],
    timeout_seconds: float = 12.0,
) -> FundProfileRefreshState:
    key = str(fund_code or "").strip().upper()
    if not key:
        return FundProfileRefreshState("IDLE")

    now = monotonic()
    with _LOCK:
        job = _JOBS.get(key)
        if job is not None:
            if job.status == "RUNNING":
                if now - job.started_at > timeout_seconds:
                    job.generation += 1
                    job.status = "TIMEOUT"
                    return FundProfileRefreshState("TIMEOUT")
                return FundProfileRefreshState("RUNNING")
            if job.status == "DONE":
                result = job.result
                del _JOBS[key]
                return FundProfileRefreshState("DONE", result=result)
            if job.status == "FAILED":
                err = job.error
                del _JOBS[key]
                return FundProfileRefreshState("FAILED", error=err)
            if job.status == "TIMEOUT":
                del _JOBS[key]
                return FundProfileRefreshState("TIMEOUT")

        job = _Job(started_at=now)
        _JOBS[key] = job
        generation = job.generation

    Thread(target=_run, args=(key, generation, loader), daemon=True).start()
    return FundProfileRefreshState("RUNNING")

def _reset_for_tests() -> None:
    with _LOCK:
        _JOBS.clear()
""", encoding="utf-8")

test.parent.mkdir(parents=True, exist_ok=True)
test.write_text("""from __future__ import annotations

import time

from backend.app.funds.fund_profile_nonblocking_refresh import (
    _reset_for_tests,
    queue_selected_fund_auto_refresh,
)

def setup_function():
    _reset_for_tests()

def test_nonblocking_first_call():
    def loader():
        time.sleep(0.2)
        return "ok"
    t0 = time.perf_counter()
    state = queue_selected_fund_auto_refresh("AAA", loader=loader, timeout_seconds=2)
    assert state.status == "RUNNING"
    assert time.perf_counter() - t0 < 0.1

def test_result_collected_later():
    queue_selected_fund_auto_refresh("BBB", loader=lambda: "ok", timeout_seconds=2)
    deadline = time.time() + 1
    while time.time() < deadline:
        state = queue_selected_fund_auto_refresh("BBB", loader=lambda: "x", timeout_seconds=2)
        if state.status == "DONE":
            assert state.result == "ok"
            return
        time.sleep(0.01)
    raise AssertionError("background refresh did not finish")

def test_failure_isolated():
    def loader():
        raise RuntimeError("boom")
    queue_selected_fund_auto_refresh("CCC", loader=loader, timeout_seconds=2)
    deadline = time.time() + 1
    while time.time() < deadline:
        state = queue_selected_fund_auto_refresh("CCC", loader=lambda: "x", timeout_seconds=2)
        if state.status == "FAILED":
            assert "boom" in (state.error or "")
            return
        time.sleep(0.01)
    raise AssertionError("failure not surfaced")

def test_timeout_bounded():
    def loader():
        time.sleep(0.2)
        return "late"
    queue_selected_fund_auto_refresh("DDD", loader=loader, timeout_seconds=0.01)
    time.sleep(0.03)
    state = queue_selected_fund_auto_refresh("DDD", loader=lambda: "x", timeout_seconds=0.01)
    assert state.status == "TIMEOUT"
""", encoding="utf-8")
