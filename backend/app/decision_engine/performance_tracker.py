from __future__ import annotations

from typing import Any


def calculate_decision_performance(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Karar performans özetini oluşturur."""

    total = len(records)

    successful = sum(
        1
        for item in records
        if item.get("result") == "positive"
    )

    return {
        "total_decisions": total,
        "successful_decisions": successful,
        "success_rate": round(successful / total, 2) if total else 0,
    }
