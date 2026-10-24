from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.ui.financial_intelligence_renderer_payload import (
    build_financial_intelligence_renderer_payload,
)


def _fmt_score(value: Any) -> str:
    if value is None:
        return "—"

    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    if d == d.to_integral_value():
        return f"{int(d)}/100"

    return f"{d.normalize()}/100"


def _fmt_price(value: Any) -> str:
    if value is None:
        return "—"

    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    return f"{d.quantize(Decimal('0.01')):f}"


def _risk_label(value: Any) -> str:
    mapping = {
        "LOW": "Düşük",
        "MEDIUM": "Orta",
        "HIGH": "Yüksek",
    }

    if value is None:
        return "—"

    key = str(value).strip().upper()
    return mapping.get(key, str(value))


def _valuation_label(value: Any) -> str:
    mapping = {
        "VERY_EXPENSIVE": "ok Pahalı",
        "EXPENSIVE": "Pahalı",
        "FAIR": "Makul",
        "ATTRACTIVE": "Cazip",
        "CHEAP": "Ucuz",
        "VERY_CHEAP": "ok Ucuz",
        "OVERVALUED": "Pahalı",
        "UNDERVALUED": "Ucuz",
    }

    if value is None:
        return "—"

    key = str(value).strip().upper()
    return mapping.get(key, str(value))


def build_financial_intelligence_presentation_contract(
    project_root: str | Path,
    *,
    symbol: str | None = None,
) -> dict[str, Any]:

    payload = build_financial_intelligence_renderer_payload(
        project_root,
        symbol=symbol,
    )

    if payload.get("status") != "PASS":
        return {
            "status": payload.get("status"),
            "symbol": payload.get("symbol"),
            "eligible_symbols": list(
                payload.get("eligible_symbols") or []
            ),
            "cards": [],
            "valuation": {},
            "mode": "READ_ONLY_PRESENTATION_CONTRACT",
        }

    cards = [
        {
            "key": "financial_health",
            "label": "Financial Health",
            "raw_value": payload.get("financial_health"),
            "display_value": _fmt_score(
                payload.get("financial_health")
            ),
        },
        {
            "key": "cash_quality",
            "label": "Cash Quality",
            "raw_value": payload.get("cash_quality"),
            "display_value": _fmt_score(
                payload.get("cash_quality")
            ),
        },
        {
            "key": "capital_efficiency",
            "label": "Capital Efficiency",
            "raw_value": payload.get("capital_efficiency"),
            "display_value": _fmt_score(
                payload.get("capital_efficiency")
            ),
        },
        {
            "key": "risk",
            "label": "Risk",
            "raw_value": payload.get("risk"),
            "display_value": _risk_label(
                payload.get("risk")
            ),
        },
    ]

    valuation = {
        "current_price": {
            "label": "Current Price",
            "raw_value": payload.get("current_price"),
            "display_value": _fmt_price(
                payload.get("current_price")
            ),
        },
        "attractive_entry_price": {
            "label": "Attractive Entry Price",
            "raw_value": payload.get(
                "attractive_entry_price"
            ),
            "display_value": _fmt_price(
                payload.get(
                    "attractive_entry_price"
                )
            ),
        },
        "valuation_status": {
            "label": "Valuation Status",
            "raw_value": payload.get(
                "valuation_status"
            ),
            "display_value": _valuation_label(
                payload.get(
                    "valuation_status"
                )
            ),
        },
    }

    return {
        "status": "PASS",
        "symbol": payload.get("symbol"),
        "eligible_symbols": list(
            payload.get("eligible_symbols") or []
        ),
        "panel_status": payload.get("panel_status"),
        "cards": cards,
        "valuation": valuation,
        "bank_production": payload.get("bank_production"),
        "panel_artifact": payload.get(
            "panel_artifact"
        ),
        "mode": "READ_ONLY_PRESENTATION_CONTRACT",
    }


__all__ = [
    "build_financial_intelligence_presentation_contract"
]
