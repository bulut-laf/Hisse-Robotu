from __future__ import annotations

from typing import Any


def validate_end_to_end_flow(
    flow: dict[str, Any],
) -> dict[str, Any]:
    """Gerçek kullanım zincirini uçtan uca kontrol eder."""

    checks = {
        "data": bool(flow.get("data")),
        "analysis": bool(flow.get("analysis")),
        "sector": bool(flow.get("sector")),
        "risk": bool(flow.get("risk")),
        "decision": bool(flow.get("decision")),
        "dashboard": bool(flow.get("dashboard")),
        "report": bool(flow.get("report")),
    }

    return {
        "checks": checks,
        "ready": all(checks.values()) if checks else False,
    }
