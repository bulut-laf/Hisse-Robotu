from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class DailyAIOperationContext:
    available: bool
    review_date: str | None
    current_day: bool
    report_count: int
    provider: str
    model: str
    summary: str | None
    positive_factors: tuple[str, ...]
    risk_factors: tuple[str, ...]
    conflicting_points: tuple[str, ...]
    watch_items: tuple[str, ...]
    previous_date: str | None
    added_risks: tuple[str, ...]
    resolved_risks: tuple[str, ...]
    added_positive_factors: tuple[str, ...]
    removed_positive_factors: tuple[str, ...]


def _clean_items(values: Any) -> tuple[str, ...]:
    if not isinstance(values, list):
        return ()

    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        text = str(value).strip()
        if not text:
            continue

        key = text.casefold()
        if key in seen:
            continue

        seen.add(key)
        result.append(text)

    return tuple(result)


def _difference(
    current: Iterable[str],
    previous: Iterable[str],
) -> tuple[str, ...]:
    previous_keys = {
        str(item).strip().casefold()
        for item in previous
        if str(item).strip()
    }

    return tuple(
        item
        for item in current
        if item.casefold() not in previous_keys
    )


def _record_sort_key(record: dict[str, Any]) -> tuple[str, str]:
    return (
        str(record.get("date", "")),
        str(record.get("created_at", "")),
    )


def build_daily_ai_operation_context(
    records: Iterable[dict[str, Any]],
    *,
    today: str | None = None,
) -> DailyAIOperationContext:
    """Arşivlenmiş AI değerlendirmelerini operasyon paneli için özetler.

    Yeni AI çağrısı yapmaz.
    Teknik skor, işlem sinyali veya AL/SAT kararı üretmez.
    """

    valid_records = [
        item
        for item in records
        if isinstance(item, dict)
        and str(item.get("date", "")).strip()
        and isinstance(item.get("output"), dict)
    ]

    if not valid_records:
        return DailyAIOperationContext(
            available=False,
            review_date=None,
            current_day=False,
            report_count=0,
            provider="",
            model="",
            summary=None,
            positive_factors=(),
            risk_factors=(),
            conflicting_points=(),
            watch_items=(),
            previous_date=None,
            added_risks=(),
            resolved_risks=(),
            added_positive_factors=(),
            removed_positive_factors=(),
        )

    valid_records.sort(key=_record_sort_key)

    latest_date = str(valid_records[-1]["date"])
    same_day = [
        item
        for item in valid_records
        if str(item.get("date")) == latest_date
    ]
    current = max(same_day, key=_record_sort_key)

    previous_candidates = [
        item
        for item in valid_records
        if str(item.get("date")) < latest_date
    ]
    previous = (
        max(previous_candidates, key=_record_sort_key)
        if previous_candidates
        else None
    )

    current_output = current.get("output", {})
    previous_output = previous.get("output", {}) if previous else {}

    current_risks = _clean_items(current_output.get("risk_factors", []))
    previous_risks = _clean_items(previous_output.get("risk_factors", []))
    current_positive = _clean_items(current_output.get("positive_factors", []))
    previous_positive = _clean_items(previous_output.get("positive_factors", []))

    today_value = today or date.today().isoformat()

    return DailyAIOperationContext(
        available=True,
        review_date=latest_date,
        current_day=latest_date == today_value,
        report_count=int(current.get("report_count", 0) or 0),
        provider=str(current.get("provider", "") or ""),
        model=str(current.get("model", "") or ""),
        summary=(
            str(current_output.get("summary")).strip()
            if current_output.get("summary")
            else None
        ),
        positive_factors=current_positive,
        risk_factors=current_risks,
        conflicting_points=_clean_items(current_output.get("conflicting_points", [])),
        watch_items=_clean_items(current_output.get("watch_items", [])),
        previous_date=(str(previous.get("date")) if previous is not None else None),
        added_risks=_difference(current_risks, previous_risks),
        resolved_risks=_difference(previous_risks, current_risks),
        added_positive_factors=_difference(current_positive, previous_positive),
        removed_positive_factors=_difference(previous_positive, current_positive),
    )


def load_daily_ai_operation_context(
    data_root: str | Path,
    *,
    today: str | None = None,
) -> DailyAIOperationContext:
    """Sprint-139C AI arşivini okuyup operasyon bağlamı oluşturur."""

    root = Path(data_root) / "market_context_ai_evaluations"
    records: list[dict[str, Any]] = []

    if root.exists():
        for path in root.glob("*/*.json"):
            if not path.is_file():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                records.append(payload)

    return build_daily_ai_operation_context(records, today=today)
