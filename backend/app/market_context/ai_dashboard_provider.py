from __future__ import annotations

from typing import Any


def build_ai_dashboard_payload(
    evaluation: dict[str, Any] | None,
) -> dict[str, Any]:
    """AI dashboard görünümü için veri sağlayıcı hazırlığı.

    Sunum verisi üretir.
    Karar veya işlem sinyali üretmez.
    """

    if not evaluation:
        return {
            "available": False,
            "summary": None,
            "positive_items": [],
            "risk_items": [],
            "change_items": [],
        }

    return {
        "available": True,
        "summary": evaluation.get("summary"),
        "positive_items": list(evaluation.get("positive_items", [])),
        "risk_items": list(evaluation.get("risk_items", [])),
        "change_items": list(evaluation.get("change_items", [])),
    }
