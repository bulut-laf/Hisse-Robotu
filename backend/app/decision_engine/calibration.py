from __future__ import annotations

from typing import Any


def calibrate_decision_model(
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """Karar modeli kalibrasyon özeti oluşturur."""

    success_rate = metrics.get("success_rate", 0)

    if success_rate >= 0.70:
        status = "stable"
    elif success_rate >= 0.50:
        status = "review"
    else:
        status = "needs_improvement"

    return {
        "status": status,
        "success_rate": success_rate,
    }
