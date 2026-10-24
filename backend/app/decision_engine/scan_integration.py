from __future__ import annotations

from typing import Any


def integrate_scan_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Toplu tarama sonuçlarını karar motoru formatına taşır."""

    results = []

    for item in candidates:
        results.append(
            {
                "symbol": item.get("symbol"),
                "sector": item.get("sector"),
                "score": item.get("score", 0),
                "decision_ready": True,
            }
        )

    return results
