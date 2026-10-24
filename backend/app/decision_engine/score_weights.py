from __future__ import annotations

from typing import Any


DEFAULT_WEIGHTS = {
    "market": 20,
    "sector": 20,
    "technical": 30,
    "momentum": 15,
    "risk": 15,
}


def calculate_weighted_score(
    factors: dict[str, float],
) -> dict[str, Any]:
    """Faktör ağırlıkları ile birleşik karar skoru oluşturur.

    Karar desteği sağlar.
    Tek başına işlem emri üretmez.
    """

    score = 0.0

    for key, weight in DEFAULT_WEIGHTS.items():
        score += factors.get(key, 0) * weight / 100

    return {
        "score": round(score, 2),
        "weights": DEFAULT_WEIGHTS.copy(),
    }
