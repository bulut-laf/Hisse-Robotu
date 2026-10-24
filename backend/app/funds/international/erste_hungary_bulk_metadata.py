from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
import time
from typing import Any, Callable, Iterable

from .erste_hungary_comparison import (
    ErsteComparisonFund,
    fetch_single_fund_comparison,
)


@dataclass(frozen=True, slots=True)
class BulkCollectionSummary:
    target_count: int
    already_completed_count: int
    attempted_count: int
    success_count: int
    failure_count: int
    completed_total_count: int


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def fund_to_record(fund: ErsteComparisonFund) -> dict[str, Any]:
    raw = asdict(fund)
    return {key: _json_value(value) for key, value in raw.items()}


def load_completed_isins(jsonl_path: Path) -> set[str]:
    if not jsonl_path.exists():
        return set()

    completed: set[str] = set()
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue

            isin = str(payload.get("isin") or "").strip().upper()
            if isin:
                completed.add(isin)

    return completed


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        )


def collect_bulk_metadata(
    isins: Iterable[str],
    *,
    success_jsonl: Path,
    failure_jsonl: Path,
    fetcher: Callable[..., ErsteComparisonFund] = fetch_single_fund_comparison,
    timeout_seconds: float = 40.0,
    request_delay_seconds: float = 0.08,
    progress_callback: Callable[[int, int, int, int, str], None] | None = None,
) -> BulkCollectionSummary:
    normalized = tuple(
        dict.fromkeys(
            isin.strip().upper()
            for isin in isins
            if isin and isin.strip()
        )
    )

    completed_before = load_completed_isins(success_jsonl)
    pending = [isin for isin in normalized if isin not in completed_before]

    success_count = 0
    failure_count = 0

    for index, isin in enumerate(pending, start=1):
        try:
            fund = fetcher(
                isin,
                timeout_seconds=timeout_seconds,
            )
            record = fund_to_record(fund)
            append_jsonl(success_jsonl, record)
            success_count += 1
            state = "SUCCESS"
        except Exception as exc:
            append_jsonl(
                failure_jsonl,
                {
                    "isin": isin,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:1000],
                },
            )
            failure_count += 1
            state = "FAIL"

        if progress_callback is not None:
            progress_callback(
                index,
                len(pending),
                success_count,
                failure_count,
                state,
            )

        if request_delay_seconds > 0 and index < len(pending):
            time.sleep(request_delay_seconds)

    completed_after = load_completed_isins(success_jsonl)

    return BulkCollectionSummary(
        target_count=len(normalized),
        already_completed_count=len(completed_before.intersection(normalized)),
        attempted_count=len(pending),
        success_count=success_count,
        failure_count=failure_count,
        completed_total_count=len(completed_after.intersection(normalized)),
    )