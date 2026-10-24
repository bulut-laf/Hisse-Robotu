from __future__ import annotations

from decimal import Decimal

from .f1_rank_history import fund_category_rank_history_store


def f1_rank_metrics_by_fund() -> dict[str, tuple[Decimal, int]]:
    store = fund_category_rank_history_store()
    rows = tuple(store.list_records())

    grouped: dict[str, list] = {}
    for row in rows:
        grouped.setdefault(row.canonical_fund_id, []).append(row)

    result: dict[str, tuple[Decimal, int]] = {}

    for fund_id, items in grouped.items():
        ordered = sorted(items, key=lambda r: r.observation_date)
        if len(ordered) < 2:
            continue

        previous = ordered[-2]
        current = ordered[-1]

        if current.category_fund_count <= 0:
            continue
        if current.category_rank <= 0:
            continue
        if current.category_rank > current.category_fund_count:
            continue

        percentile = (
            Decimal(current.category_fund_count - current.category_rank + 1)
            / Decimal(current.category_fund_count)
        )

        rank_change = previous.category_rank - current.category_rank
        result[fund_id] = (percentile, rank_change)

    return result
