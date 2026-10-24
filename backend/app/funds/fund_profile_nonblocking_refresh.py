from __future__ import annotations

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
