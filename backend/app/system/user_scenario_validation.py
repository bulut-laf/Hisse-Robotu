from __future__ import annotations

from typing import Any


def validate_user_scenarios(
    scenarios: dict[str, Any],
) -> dict[str, Any]:
    """Gerçek kullanım senaryolarını kontrol eder."""

    checks = {
        "daily_analysis": bool(scenarios.get("daily_analysis")),
        "candidate_review": bool(scenarios.get("candidate_review")),
        "portfolio_check": bool(scenarios.get("portfolio_check")),
        "report_access": bool(scenarios.get("report_access")),
    }

    return {
        "checks": checks,
        "ready": all(checks.values()) if checks else False,
    }
