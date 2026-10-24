from __future__ import annotations

from typing import Any


def add_decision_labels(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Tarama adaylarına karar etiketlerini ekler."""

    results = []

    for item in candidates:
        results.append(
            {
                **item,
                "decision_label": item.get(
                    "decision_label",
                    "İZLE",
                ),
                "decision_available": True,
            }
        )

    return results
