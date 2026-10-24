from __future__ import annotations

from typing import Any


def validate_performance_metrics(
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """Sistem performans ölçümlerini değerlendirir."""

    checks = {
        "analysis_time": metrics.get("analysis_time", 0) >= 0,
        "report_time": metrics.get("report_time", 0) >= 0,
        "data_processing": bool(metrics.get("data_processing", False)),
    }

    return {
        "checks": checks,
        "ready": all(checks.values()),
    }
