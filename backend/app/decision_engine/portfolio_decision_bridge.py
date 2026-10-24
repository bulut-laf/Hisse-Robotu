from __future__ import annotations

from typing import Any


def evaluate_portfolio_position(
    position: dict[str, Any],
) -> dict[str, Any]:
    """Mevcut pozisyonları karar motoru bağlamına taşır."""

    risk = position.get("risk", "unknown")
    trend = position.get("trend", "unknown")

    if risk == "high" or trend == "broken":
        status = "SAT ADAYI"
    elif trend == "positive" and risk == "controlled":
        status = "TUT"
    else:
        status = "İZLE"

    return {
        "symbol": position.get("symbol"),
        "decision_label": status,
        "risk": risk,
        "trend": trend,
    }
