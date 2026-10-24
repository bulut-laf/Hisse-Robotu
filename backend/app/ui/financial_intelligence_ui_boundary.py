from __future__ import annotations

from pathlib import Path
from typing import Any

from app.ui.financial_intelligence_presentation_contract import (
    build_financial_intelligence_presentation_contract,
)


def build_financial_intelligence_ui_boundary(
    project_root: str | Path,
    *,
    symbol: str | None = None,
) -> dict[str, Any]:

    presentation = build_financial_intelligence_presentation_contract(
        project_root,
        symbol=symbol,
    )

    if presentation.get("status") != "PASS":
        return {
            "status": presentation.get("status"),
            "symbol": presentation.get("symbol"),
            "eligible_symbols": list(
                presentation.get("eligible_symbols") or []
            ),
            "metric_cards": [],
            "valuation_rows": [],
            "mode": "READ_ONLY_UI_CONSUMPTION_BOUNDARY",
        }

    cards = list(presentation.get("cards") or [])
    valuation = dict(presentation.get("valuation") or {})

    metric_cards = [
        {
            "key": row["key"],
            "label": row["label"],
            "value": row["display_value"],
            "raw_value": row["raw_value"],
        }
        for row in cards
    ]

    valuation_rows = []

    for key in (
        "current_price",
        "attractive_entry_price",
        "valuation_status",
    ):
        row = valuation.get(key)

        if row:
            valuation_rows.append({
                "key": key,
                "label": row["label"],
                "value": row["display_value"],
                "raw_value": row["raw_value"],
            })

    return {
        "status": "PASS",
        "symbol": presentation.get("symbol"),
        "eligible_symbols": list(
            presentation.get("eligible_symbols") or []
        ),
        "panel_status": presentation.get("panel_status"),
        "metric_cards": metric_cards,
        "valuation_rows": valuation_rows,
        "bank_production": presentation.get("bank_production"),
        "panel_artifact": presentation.get("panel_artifact"),
        "mode": "READ_ONLY_UI_CONSUMPTION_BOUNDARY",
    }


__all__ = [
    "build_financial_intelligence_ui_boundary"
]
