from __future__ import annotations

from typing import Any


def evaluate_historical_results(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Karar sonuçlarının geçmiş performans özetini çıkarır."""

    total = len(records)

    successful = sum(
        1
        for item in records
        if item.get("outcome") == "positive"
    )

    return {
        "total": total,
        "successful": successful,
        "success_rate": round(
            successful / total,
            2,
        ) if total else 0,
    }
