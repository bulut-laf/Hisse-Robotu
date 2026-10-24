from __future__ import annotations

from typing import Any


def build_decision_report(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Aday için okunabilir karar destek raporu oluşturur.

    Sonuçları özetler.
    Tek başına işlem emri üretmez.
    """

    return {
        "symbol": candidate.get("symbol"),
        "priority": candidate.get("priority"),
        "score": candidate.get("score"),
        "sector": candidate.get("sector"),
        "risk": candidate.get("risk"),
    }
