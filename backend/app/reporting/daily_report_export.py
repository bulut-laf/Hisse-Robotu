from __future__ import annotations

from typing import Any


def export_daily_report_data(
    report: dict[str, Any],
) -> dict[str, Any]:
    """Günlük raporu dışa aktarma formatına hazırlar."""

    return {
        "date": report.get("date"),
        "market": report.get("market"),
        "sectors": report.get("sectors", []),
        "candidates": report.get("candidates", []),
        "positions": report.get("positions", []),
    }
