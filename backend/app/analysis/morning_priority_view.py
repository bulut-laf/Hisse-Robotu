from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class MorningPriorityView:
    total_candidates: int
    urgent_count: int
    blocked_count: int
    top_priority_symbols: tuple[str, ...]


def build_morning_priority_view(
    candidates: Iterable[object],
    limit: int = 3,
) -> MorningPriorityView:
    items = tuple(candidates)

    priority = [
        str(getattr(item, "symbol", "")).upper()
        for item in items
        if getattr(item, "research_priority", "") == "HIGH"
        and not bool(getattr(item, "data_blocked", False))
    ]

    blocked = sum(
        bool(getattr(item, "data_blocked", False))
        for item in items
    )

    return MorningPriorityView(
        total_candidates=len(items),
        urgent_count=len(priority),
        blocked_count=blocked,
        top_priority_symbols=tuple(priority[:limit]),
    )
