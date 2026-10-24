from __future__ import annotations

from typing import Any


def build_portfolio_decision_panel(
    positions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Portföy pozisyonlarını karar paneli formatına hazırlar."""

    return [
        {
            "symbol": item.get("symbol"),
            "sector": item.get("sector"),
            "trend": item.get("trend"),
            "risk": item.get("risk"),
            "decision": item.get("decision", "İZLE"),
        }
        for item in positions
    ]
