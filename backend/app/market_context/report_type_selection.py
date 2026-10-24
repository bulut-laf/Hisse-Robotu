from __future__ import annotations

from backend.app.market_context.report_types import REPORT_TYPES


def normalize_report_type(value: str | None) -> str:
    if value in REPORT_TYPES:
        return value
    return "market_commentary"
