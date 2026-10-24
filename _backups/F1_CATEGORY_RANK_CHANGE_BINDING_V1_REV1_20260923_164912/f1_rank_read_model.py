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

        # TEFAS category rank: 1 is best. Convert rank to a [0,1] strength
        # percentile where higher is better, matching the existing F1 mapper.
        percentile = (
            Decimal(current.category_fund_count - current.category_rank + 1)
            / Decimal(current.category_fund_count)
        )

        # Existing F1 mapper treats positive change as improvement.
        # Since a lower ordinal rank is better, previous-current > 0 means improvement.
        rank_change = previous.category_rank - current.category_rank

        result[fund_id] = (percentile, rank_change)

    return result
