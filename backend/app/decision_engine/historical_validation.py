from __future__ import annotations

from typing import Any


def validate_historical_decision(
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Karar sonuçlarının tarihsel doğrulama özeti.

    Kalibrasyon için temel istatistik üretir.
    Gelecek kararları tek başına belirlemez.
    """

    total = len(decisions)

    positive = sum(
        1 for item in decisions
        if item.get("result") == "positive"
    )

    return {
        "total": total,
        "positive": positive,
        "accuracy_hint": round(
            positive / total, 2
        ) if total else 0,
    }
