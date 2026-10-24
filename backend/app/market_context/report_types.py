from __future__ import annotations

REPORT_TYPES = {
    "market_commentary",
    "kap_news",
    "daily_recommendation",
    "weekly_recommendation",
    "model_portfolio",
    "target_price_report",
    "sector_view",
}

DEFAULT_REPORT_TYPE = "market_commentary"


def is_valid_report_type(value: str) -> bool:
    return value in REPORT_TYPES
