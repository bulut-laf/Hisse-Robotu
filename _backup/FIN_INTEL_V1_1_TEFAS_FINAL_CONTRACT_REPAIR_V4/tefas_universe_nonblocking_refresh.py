from __future__ import annotations

from dataclasses import dataclass
from threading import Lock, Thread
from time import monotonic
from typing import Any, Callable


@dataclass(frozen=True)
class TefasUniverseRefreshState:
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
_JOB: _Job | None = None


def _worker(generation: int, loader: Callable[[], Any]) -> None:
    global _JOB
    try:
        result = loader()
    except Exception as exc:
        with _LOCK:
            if _JOB is not None and _JOB.generation == generation:
                _JOB.status = "FAILED"
                _JOB.error = str(exc)
        return

    with _LOCK:
        if _JOB is not None and _JOB.generation == generation:
            _JOB.status = "DONE"
            _JOB.result = result


def queue_tefas_universe_refresh(
    *,
    loader: Callable[[], Any],
    timeout_seconds: float = 20.0,
) -> TefasUniverseRefreshState:
    global _JOB
    now = monotonic()

    with _LOCK:
        if _JOB is not None:
            if _JOB.status == "RUNNING":
                if now - _JOB.started_at > timeout_seconds:
                    _JOB.generation += 1
                    _JOB.status = "TIMEOUT"
                    return TefasUniverseRefreshState(status="TIMEOUT")
                return TefasUniverseRefreshState(status="RUNNING")

            if _JOB.status == "DONE":
                result = _JOB.result
                _JOB = None
                return TefasUniverseRefreshState(status="DONE", result=result)

            if _JOB.status == "FAILED":
                error = _JOB.error
                _JOB = None
                return TefasUniverseRefreshState(status="FAILED", error=error)

            if _JOB.status == "TIMEOUT":
                _JOB = None
                return TefasUniverseRefreshState(status="TIMEOUT")

        generation = 1
        _JOB = _Job(generation=generation, started_at=now)

    Thread(
        target=_worker,
        args=(generation, loader),
        daemon=True,
        name="tefas-universe-refresh",
    ).start()
    return TefasUniverseRefreshState(status="STARTED")


def _reset_for_tests() -> None:
    global _JOB
    with _LOCK:
        _JOB = None
