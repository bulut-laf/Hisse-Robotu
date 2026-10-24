from __future__ import annotations

from typing import Any


def calculate_sector_stock_priority(
    sector_score: float,
    technical_score: float,
) -> dict[str, Any]:
    """Sektör ve teknik görünümü birleştirir.

    Karar desteği için öncelik skoru üretir.
    Tek başına işlem emri oluşturmaz.
    """

    score = (sector_score * 0.4) + (technical_score * 0.6)

    if score >= 75:
        priority = "high"
    elif score >= 50:
        priority = "medium"
    else:
        priority = "low"

    return {
        "priority_score": round(score, 2),
        "priority": priority,
    }
