from __future__ import annotations

from typing import Any


def calculate_sector_strength(
    performance: float,
    volume_change: float = 0.0,
) -> dict[str, Any]:
    """Sektör güç değerlendirmesi.

    Sadece sektör bağlamı üretir.
    İşlem sinyali üretmez.
    """

    score = performance + (volume_change * 0.25)

    if score >= 5:
        status = "strong"
    elif score <= -5:
        status = "weak"
    else:
        status = "neutral"

    return {
        "score": round(score, 2),
        "status": status,
    }
