from __future__ import annotations

from typing import Any


REQUIRED_AI_FIELDS = {
    "summary",
    "positive_items",
    "risk_items",
    "change_items",
}


def validate_ai_dashboard_payload(
    payload: dict[str, Any],
) -> bool:
    """AI V1 zinciri için son veri kontrolü.

    Karar üretmez.
    Sadece yapı bütünlüğünü kontrol eder.
    """

    if payload.get("available") is not True:
        return False

    return REQUIRED_AI_FIELDS.issubset(payload.keys())
