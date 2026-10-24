from __future__ import annotations

from typing import Any


def validate_ai_memory_chain(
    archive: dict[str, Any],
    comparison: dict[str, Any],
    trend: dict[str, Any],
    view: list[dict[str, Any]],
) -> bool:
    """AI hafıza zinciri bütünlük kontrolü.

    Sadece veri akışını doğrular.
    İşlem kararı üretmez.
    """

    if not archive:
        return False

    if "summary" not in archive:
        return False

    if "risk_changes" not in comparison and "positive_changes" not in comparison:
        return False

    if "count" not in trend:
        return False

    if not isinstance(view, list):
        return False

    return True
