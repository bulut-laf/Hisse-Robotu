from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Iterable


RANK_HISTORY_VERSION = "erste-hungary-rank-history-v1"


@dataclass(frozen=True, slots=True)
class RankHistoryPoint:
    rank_date: date
    isin: str
    category_normalized: str
    rank_position: int
    category_size: int
    rank_percentile: Decimal
    rank_score: Decimal


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def rank_point_from_seed(
    row: dict[str, Any],
    *,
    rank_date: date,
) -> RankHistoryPoint | None:
    if row.get("rank_position") is None:
        return None
    if row.get("rank_percentile") is None:
        return None
    if row.get("rank_score") is None:
        return None
    if not row.get("category_normalized"):
        return None

    return RankHistoryPoint(
        rank_date=rank_date,
        isin=str(row["isin"]).strip().upper(),
        category_normalized=str(row["category_normalized"]),
        rank_position=int(row["rank_position"]),
        category_size=int(row["category_size"]),
        rank_percentile=_decimal(row["rank_percentile"]),
        rank_score=_decimal(row["rank_score"]),
    )


def load_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("ERSTE_RANK_HISTORY_NOT_LIST")
    return payload


def seed_rank_history(
    seed_rows: Iterable[dict[str, Any]],
    *,
    rank_date: date,
    history_path: Path,
) -> dict[str, int]:
    history = load_history(history_path)

    existing_keys = {
        (
            str(item.get("rank_date")),
            str(item.get("isin")).strip().upper(),
        )
        for item in history
    }

    inserted = 0
    skipped_existing = 0

    for row in seed_rows:
        point = rank_point_from_seed(row, rank_date=rank_date)
        if point is None:
            continue

        key = (point.rank_date.isoformat(), point.isin)
        if key in existing_keys:
            skipped_existing += 1
            continue

        history.append(
            {
                "rank_date": point.rank_date.isoformat(),
                "isin": point.isin,
                "category_normalized": point.category_normalized,
                "rank_position": point.rank_position,
                "category_size": point.category_size,
                "rank_percentile": str(point.rank_percentile),
                "rank_score": str(point.rank_score),
            }
        )
        existing_keys.add(key)
        inserted += 1

    history.sort(
        key=lambda item: (
            str(item["rank_date"]),
            str(item["isin"]),
        )
    )

    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    unique_dates = {
        str(item["rank_date"])
        for item in history
    }
    unique_isins = {
        str(item["isin"])
        for item in history
    }

    return {
        "inserted_count": inserted,
        "skipped_existing_count": skipped_existing,
        "history_row_count": len(history),
        "unique_date_count": len(unique_dates),
        "unique_isin_count": len(unique_isins),
    }


def two_date_fund_count(history: Iterable[dict[str, Any]]) -> int:
    dates_by_isin: dict[str, set[str]] = {}

    for item in history:
        isin = str(item.get("isin") or "").strip().upper()
        rank_date = str(item.get("rank_date") or "")
        if isin and rank_date:
            dates_by_isin.setdefault(isin, set()).add(rank_date)

    return sum(
        1
        for dates in dates_by_isin.values()
        if len(dates) >= 2
    )