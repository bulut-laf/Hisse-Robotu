from __future__ import annotations

from typing import Any


def validate_data_flow(
    flow: dict[str, Any],
) -> dict[str, Any]:
    """Verinin ana çalışma zincirinden geçtiğini kontrol eder."""

    checks = {
        "source": bool(flow.get("source")),
        "analysis": bool(flow.get("analysis")),
        "decision": bool(flow.get("decision")),
        "dashboard": bool(flow.get("dashboard")),
        "report": bool(flow.get("report")),
    }

    return {
        "checks": checks,
        "ready": all(checks.values()),
    }
