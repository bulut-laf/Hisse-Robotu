from pathlib import Path
import sys

root = Path(sys.argv[1])
ui = root / "backend/app/ui/fund_analysis_center.py"
helper = root / "backend/app/funds/fund_profile_nonblocking_refresh.py"
test = root / "backend/tests/test_fund_profile_nonblocking_refresh_v1.py"

text = ui.read_text(encoding="utf-8")

old_import = "from backend.app.funds.fund_auto_refresh import auto_refresh_selected_fund_if_due\n"
new_import = """from backend.app.funds.fund_auto_refresh import auto_refresh_selected_fund_if_due
from backend.app.funds.fund_profile_nonblocking_refresh import (
    queue_selected_fund_auto_refresh,
)
"""

start_marker = '    if hasattr(st, "session_state"):\n        try:\n            refresh = auto_refresh_selected_fund_if_due('
end_marker = '    try:\n        profile = build_fund_profile_read_model('

start = text.find(start_marker)
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit("EXACT_REFRESH_BLOCK_NOT_FOUND")
if text.find(start_marker, start + 1) >= 0:
    raise SystemExit("EXACT_REFRESH_BLOCK_NOT_UNIQUE")

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
            st.caption(
                "Fon verisi arka planda gГјncelleniyor; son kayД±tlД± canonical veri gГ¶steriliyor."
            )
        elif refresh_state.status == "FAILED" and hasattr(st, "warning"):
            st.warning(
                "Otomatik fon yenilemesi izole edildi; son iyi veri gГ¶steriliyor. "
                + (refresh_state.error or "Bilinmeyen yenileme hatasД±")
            )
        elif refresh_state.status == "TIMEOUT" and hasattr(st, "warning"):
            st.warning(
                "Otomatik fon yenilemesi zaman sД±nД±rД±nД± aЕџtД±; son iyi veri gГ¶steriliyor."
            )
        elif refresh_state.result is not None:
            refresh = refresh_state.result
            if refresh.attempted and refresh.refreshed:
                st.caption(
                    "Otomatik gГјncelleme tamamlandД± В· "
                    f"TEFAS detay={'вњ“' if refresh.detail_written else '-'} В· "
                    f"fiyat geГ§miЕџi={'вњ“' if refresh.history_written else '-'} В· "
                    f"KAP portfГ¶y={'вњ“' if refresh.portfolio_checked else '-'} В· "
                    f"FDO={'вњ“' if refresh.fdo_checked else '-'}"
                )
            if refresh.warnings and hasattr(st, "warning"):
                st.warning(
                    "BazД± otomatik kaynaklar izole edildi: "
                    + " | ".join(refresh.warnings[:4])
                )

"""

# REV3 bug fix: replace the body first while offsets still refer to original text.
text = text[:start] + new_block + text[end:]

if old_import not in text:
    raise SystemExit("IMPORT_SEAM_NOT_FOUND")
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
    generation: int
    started_at: float
    status: str = "RUNNING"
    result: Any | None = None
    error: str | None = None


_LOCK = Lock()
_JOBS: dict[str, _Job] = {}


def _run(key: str, generation: int, loader: Callable[[], Any]) -> None:
    try:
        result = loader()
    except Exception as exc:
        with _LOCK:
            job = _JOBS.get(key)
            if job is not None and job.generation == generation:
                job.status = "FAILED"
                job.error = str(exc)
        return

    with _LOCK:
        job = _JOBS.get(key)
        if job is not None and job.generation == generation:
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
        return FundProfileRefreshState(status="IDLE")

    now = monotonic()
    with _LOCK:
        job = _JOBS.get(key)

        if job is not None and job.status == "RUNNING":
            if now - job.started_at > timeout_seconds:
                job.generation += 1
                job.status = "TIMEOUT"
                return FundProfileRefreshState(status="TIMEOUT")
            return FundProfileRefreshState(status="RUNNING")

        if job is not None and job.status == "DONE":
            result = job.result
            del _JOBS[key]
            return FundProfileRefreshState(status="DONE", result=result)

        if job is not None and job.status in {"FAILED", "TIMEOUT"}:
            state = FundProfileRefreshState(
                status=job.status,
                result=job.result,
                error=job.error,
            )
            del _JOBS[key]
            return state

        generation = 1
        _JOBS[key] = _Job(generation=generation, started_at=now)

    Thread(
        target=_run,
        args=(key, generation, loader),
        daemon=True,
        name=f"fund-profile-refresh-{key}",
    ).start()
    return FundProfileRefreshState(status="RUNNING")


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
""", encoding="utf-8")
