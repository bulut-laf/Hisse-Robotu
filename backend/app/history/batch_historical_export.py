from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from io import StringIO
import csv
import zipfile
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence


Row = Mapping[str, object]
DailyScanner = Callable[[date, str], Sequence[Row]]


@dataclass(frozen=True)
class BatchReplayRequest:
    start_date: date
    end_date: date
    universe: str = "BIST100"
    weekdays_only: bool = True

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError("Bitiş tarihi başlangıç tarihinden önce olamaz.")
        if not self.universe.strip():
            raise ValueError("Evren boş olamaz.")


@dataclass(frozen=True)
class BatchReplayDayResult:
    cut_date: date
    universe: str
    row_count: int
    rows: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class BatchReplayResult:
    request: BatchReplayRequest
    days: tuple[BatchReplayDayResult, ...]
    combined_rows: tuple[dict[str, object], ...]

    @property
    def processed_days(self) -> int:
        return len(self.days)

    @property
    def total_rows(self) -> int:
        return len(self.combined_rows)


def iter_cut_dates(request: BatchReplayRequest) -> tuple[date, ...]:
    current = request.start_date
    result: list[date] = []

    while current <= request.end_date:
        if not request.weekdays_only or current.weekday() < 5:
            result.append(current)
        current += timedelta(days=1)

    return tuple(result)


def _decorate_row(
    row: Row,
    *,
    cut_date: date,
    universe: str,
) -> dict[str, object]:
    output = dict(row)
    output["Kesim Tarihi"] = cut_date.isoformat()
    output["Evren"] = universe
    return output


def run_batch_replay(
    request: BatchReplayRequest,
    *,
    scan_day: DailyScanner,
) -> BatchReplayResult:
    day_results: list[BatchReplayDayResult] = []
    combined: list[dict[str, object]] = []

    for cut_date in iter_cut_dates(request):
        daily_rows = tuple(
            _decorate_row(row, cut_date=cut_date, universe=request.universe)
            for row in scan_day(cut_date, request.universe)
        )
        day_results.append(
            BatchReplayDayResult(
                cut_date=cut_date,
                universe=request.universe,
                row_count=len(daily_rows),
                rows=daily_rows,
            )
        )
        combined.extend(daily_rows)

    return BatchReplayResult(
        request=request,
        days=tuple(day_results),
        combined_rows=tuple(combined),
    )


def _fieldnames(rows: Iterable[Mapping[str, object]]) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()

    # Kesim Tarihi ve Evren başta yer alsın.
    for fixed in ("Kesim Tarihi", "Evren"):
        keys.append(fixed)
        seen.add(fixed)

    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                keys.append(key)

    return keys


def rows_to_csv_text(rows: Sequence[Mapping[str, object]]) -> str:
    if not rows:
        return "Kesim Tarihi,Evren\r\n"

    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=_fieldnames(rows),
        extrasaction="ignore",
        lineterminator="\r\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(dict(row))
    return buffer.getvalue()


def write_combined_csv(
    result: BatchReplayResult,
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        rows_to_csv_text(result.combined_rows),
        encoding="utf-8-sig",
        newline="",
    )
    return path


def write_daily_zip(
    result: BatchReplayResult,
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for day in result.days:
            name = f"{day.cut_date.isoformat()}_{day.universe}.csv"
            zf.writestr(
                name,
                "\ufeff" + rows_to_csv_text(day.rows),
            )

    return path


def default_combined_filename(request: BatchReplayRequest) -> str:
    safe_universe = "".join(ch for ch in request.universe if ch.isalnum() or ch in "-_")
    return (
        f"tarihsel_toplu_{safe_universe}_"
        f"{request.start_date.isoformat()}_{request.end_date.isoformat()}.csv"
    )


def default_zip_filename(request: BatchReplayRequest) -> str:
    safe_universe = "".join(ch for ch in request.universe if ch.isalnum() or ch in "-_")
    return (
        f"tarihsel_gunluk_{safe_universe}_"
        f"{request.start_date.isoformat()}_{request.end_date.isoformat()}.zip"
    )
