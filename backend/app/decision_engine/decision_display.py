from __future__ import annotations

from typing import Any


def format_decision_display(
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Karar sınıfını kullanıcı görünümüne hazırlar."""

    mapping = {
        "BUY_CANDIDATE": "AL ADAYI",
        "HOLD": "TUT",
        "SELL_CANDIDATE": "SAT ADAYI",
        "WATCH": "İZLE",
    }

    status = decision.get("decision")

    return {
        "symbol": decision.get("symbol"),
        "display_status": mapping.get(status, "İZLE"),
        "score": decision.get("score", 0),
        "reasons": decision.get("reasons", []),
    }
