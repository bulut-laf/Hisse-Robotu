from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from time import monotonic
from typing import Callable, Mapping, Sequence

from backend.app.history.batch_historical_export import (
    BatchReplayDayResult,
    BatchReplayRequest,
    BatchReplayResult,
    iter_cut_dates,
)


Row = Mapping[str, object]
DailyScanner = Callable[[date, str], Sequence[Row]]
ProgressCallback = Callable[["BatchProgress"], None]


@dataclass(frozen=True)
class BatchProgress:
    current_index: int
    total_days: int
    cut_date: date
    status: str
    row_count: int = 0
    elapsed_seconds: float = 0.0
    error: str | None = None

    @property
    def fraction(self) -> float:
        if self.total_days <= 0:
            return 1.0
        return min(max(self.current_index / self.total_days, 0.0), 1.0)


@dataclass(frozen=True)
class BatchReplayFailure:
    cut_date: date
    error: str


@dataclass(frozen=True)
class ResilientBatchReplayResult:
    batch: BatchReplayResult
    failures: tuple[BatchReplayFailure, ...]

    @property
    def failed_days(self) -> int:
        return len(self.failures)


def _decorate_row(row: Row, *, cut_date: date, universe: str) -> dict[str, object]:
    output = dict(row)
    output["Kesim Tarihi"] = cut_date.isoformat()
    output["Evren"] = universe
    return output


def run_resilient_batch_replay(
    request: BatchReplayRequest,
    *,
    scan_day: DailyScanner,
    on_progress: ProgressCallback | None = None,
    continue_on_error: bool = True,
) -> ResilientBatchReplayResult:
    dates = iter_cut_dates(request)
    total = len(dates)
    days: list[BatchReplayDayResult] = []
    combined: list[dict[str, object]] = []
    failures: list[BatchReplayFailure] = []

    for index, cut_date in enumerate(dates, start=1):
        started = monotonic()
        if on_progress is not None:
            on_progress(
                BatchProgress(
                    current_index=index,
                    total_days=total,
                    cut_date=cut_date,
                    status="started",
                )
            )

        try:
            raw_rows = scan_day(cut_date, request.universe)
            rows = tuple(
                _decorate_row(row, cut_date=cut_date, universe=request.universe)
                for row in raw_rows
            )
            day = BatchReplayDayResult(
                cut_date=cut_date,
                universe=request.universe,
                row_count=len(rows),
                rows=rows,
            )
            days.append(day)
            combined.extend(rows)

            if on_progress is not None:
                on_progress(
                    BatchProgress(
                        current_index=index,
                        total_days=total,
                        cut_date=cut_date,
                        status="completed",
                        row_count=len(rows),
                        elapsed_seconds=monotonic() - started,
                    )
                )
        except Exception as exc:
            failure = BatchReplayFailure(
                cut_date=cut_date,
                error=f"{type(exc).__name__}: {exc}",
            )
            failures.append(failure)

            if on_progress is not None:
                on_progress(
                    BatchProgress(
                        current_index=index,
                        total_days=total,
                        cut_date=cut_date,
                        status="failed",
                        elapsed_seconds=monotonic() - started,
                        error=failure.error,
                    )
                )

            if not continue_on_error:
                raise

    batch = BatchReplayResult(
        request=request,
        days=tuple(days),
        combined_rows=tuple(combined),
    )
    return ResilientBatchReplayResult(
        batch=batch,
        failures=tuple(failures),
    )
