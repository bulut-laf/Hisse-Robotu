from __future__ import annotations

from typing import Any


def validate_dashboard_connection(
    data: dict[str, Any],
) -> dict[str, Any]:
    """Dashboard veri bağlantısı kontrolü."""

    checks = {
        "decision_card": bool(data.get("decision_card")),
        "ranking": bool(data.get("ranking")),
        "sector": bool(data.get("sector")),
        "portfolio": bool(data.get("portfolio")),
        "report": bool(data.get("report")),
    }

    return {
        "checks": checks,
        "ready": all(checks.values()),
    }
