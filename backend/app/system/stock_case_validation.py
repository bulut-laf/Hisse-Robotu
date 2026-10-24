from __future__ import annotations

from typing import Any


def validate_stock_case_analysis(
    case: dict[str, Any],
) -> dict[str, Any]:
    """Tek hisse örnek analiz akışını kontrol eder."""

    checks = {
        "symbol": bool(case.get("symbol")),
        "technical": bool(case.get("technical")),
        "sector": bool(case.get("sector")),
        "risk": bool(case.get("risk")),
        "decision": bool(case.get("decision")),
    }

    return {
        "checks": checks,
        "ready": all(checks.values()) if checks else False,
    }
