from __future__ import annotations

from typing import Any


def attach_decision_to_scan(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Tarama sonuçlarına karar motoru bilgisini bağlar."""

    results = []

    for item in candidates:
        results.append(
            {
                **item,
                "decision_ready": True,
                "decision_label": item.get(
                    "decision_label",
                    "İZLE",
                ),
            }
        )

    return results
