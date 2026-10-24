from __future__ import annotations

from typing import Any


SUPPORTED_CONTEXT_TYPES = {
    "market_commentary",
    "kap_news",
    "daily_recommendation",
    "weekly_recommendation",
    "model_portfolio",
    "target_price_report",
    "sector_view",
    "global_market_commentary",
    "fund_etf_commentary",
}


def validate_context_bundle(bundle: dict[str, Any]) -> bool:
    documents = bundle.get("documents", [])

    for document in documents:
        if document.get("report_type") not in SUPPORTED_CONTEXT_TYPES:
            return False

    return True
