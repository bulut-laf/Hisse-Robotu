from __future__ import annotations

from typing import Any


def analyze_ai_history_trend(
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    """AI değerlendirme geçmişindeki eğilimleri çıkarır.

    Karar veya işlem sinyali üretmez.
    Sadece bağlamsal değişim analizi yapar.
    """

    if not history:
        return {
            "count": 0,
            "risk_frequency": {},
            "positive_frequency": {},
        }

    risk_frequency: dict[str, int] = {}
    positive_frequency: dict[str, int] = {}

    for item in history:
        for risk in item.get("risk_factors", []):
            risk_frequency[risk] = risk_frequency.get(risk, 0) + 1

        for positive in item.get("positive_factors", []):
            positive_frequency[positive] = (
                positive_frequency.get(positive, 0) + 1
            )

    return {
        "count": len(history),
        "risk_frequency": risk_frequency,
        "positive_frequency": positive_frequency,
    }
