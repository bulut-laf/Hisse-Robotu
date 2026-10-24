from __future__ import annotations

from typing import Any


def validate_decision_review(
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Üretilen kararın açıklama ve gerekçe bütünlüğünü kontrol eder."""

    checks = {
        "decision": bool(decision.get("decision")),
        "score": decision.get("score") is not None,
        "reasons": bool(decision.get("reasons")),
        "risk": bool(decision.get("risk")),
    }

    return {
        "checks": checks,
        "ready": all(checks.values()) if checks else False,
    }
