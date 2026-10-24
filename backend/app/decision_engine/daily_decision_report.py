from __future__ import annotations

from typing import Any


def build_daily_decision_report(
    candidates: list[dict[str, Any]],
    positions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Günlük karar raporu veri yapısı oluşturur."""

    return {
        "candidate_count": len(candidates),
        "position_count": len(positions),
        "candidates": candidates,
        "positions": positions,
    }
