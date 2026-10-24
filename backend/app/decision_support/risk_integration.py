from __future__ import annotations

from typing import Any


def integrate_risk_layer(
    priority_score: float,
    risk_reward: float,
    volatility: float,
) -> dict[str, Any]:
    """Öncelik skoruna risk katmanı ekler.

    Karar desteği sağlar.
    Tek başına işlem emri üretmez.
    """

    risk_adjustment = 0

    if risk_reward >= 2:
        risk_adjustment += 10

    if volatility <= 3:
        risk_adjustment += 5

    final_score = priority_score + risk_adjustment

    if final_score >= 80:
        quality = "high"
    elif final_score >= 55:
        quality = "medium"
    else:
        quality = "low"

    return {
        "risk_adjusted_score": round(final_score, 2),
        "quality": quality,
    }
