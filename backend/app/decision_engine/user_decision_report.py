from __future__ import annotations

from typing import Any


def build_user_decision_view(
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Karar motoru çıktısını kullanıcı görünümüne hazırlar."""

    return {
        "symbol": decision.get("symbol"),
        "decision": decision.get("decision"),
        "score": decision.get("score", 0),
        "sector": decision.get("sector"),
        "technical": decision.get("technical"),
        "risk": decision.get("risk"),
        "reasons": decision.get("reasons", []),
    }
