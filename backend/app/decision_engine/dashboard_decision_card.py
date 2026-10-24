from __future__ import annotations

from typing import Any


def build_decision_card(
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Karar motoru sonucunu dashboard kart yapısına dönüştürür."""

    return {
        "symbol": decision.get("symbol"),
        "status": decision.get("decision_label", "İZLE"),
        "score": decision.get("score", 0),
        "sector": decision.get("sector"),
        "risk": decision.get("risk"),
        "reasons": decision.get("reasons", []),
    }
