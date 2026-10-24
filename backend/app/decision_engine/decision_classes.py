from __future__ import annotations

from typing import Literal


DecisionClass = Literal[
    "BUY_CANDIDATE",
    "HOLD",
    "SELL_CANDIDATE",
    "WATCH",
]


def classify_decision(
    score: float,
) -> DecisionClass:
    """Karar sınıfı temelini oluşturur.

    Eşik tabanlı ilk sınıflandırmadır.
    Tek başına işlem emri üretmez.
    """

    if score >= 80:
        return "BUY_CANDIDATE"

    if score >= 60:
        return "HOLD"

    if score <= 30:
        return "SELL_CANDIDATE"

    return "WATCH"
