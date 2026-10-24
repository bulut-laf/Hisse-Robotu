from __future__ import annotations

from pathlib import Path
from typing import Any

from app.ui.financial_intelligence_renderer_contract import (
    build_financial_intelligence_renderer_contract,
)


def _exact_values(node: Any, key: str) -> list[Any]:
    out: list[Any] = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                out.append(v)
            out.extend(_exact_values(v, key))
    elif isinstance(node, list):
        for item in node:
            out.extend(_exact_values(item, key))
    return out


def _first_exact(node: Any, *keys: str) -> Any:
    for key in keys:
        values = _exact_values(node, key)
        if values:
            return values[0]
    return None


def _score_value(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("score", "value", "total_score", "overall_score"):
            if key in value and value[key] is not None:
                return value[key]
    return value


def build_financial_intelligence_renderer_payload(
    project_root: str | Path,
    *,
    symbol: str | None = None,
) -> dict[str, Any]:
    contract = build_financial_intelligence_renderer_contract(
        project_root,
        symbol=symbol,
    )

    if contract.get("status") != "PASS":
        return {
            "status": contract.get("status"),
            "symbol": contract.get("symbol"),
            "eligible_symbols": list(contract.get("eligible_symbols") or []),
            "panel_status": None,
            "coverage_status": None,
            "decision_support_status": None,
            "financial_health": None,
            "cash_quality": None,
            "capital_efficiency": None,
            "risk": None,
            "current_price": None,
            "attractive_entry_price": None,
            "valuation_status": None,
            "panel_artifact": contract.get("panel_artifact"),
            "mode": "READ_ONLY_RENDERER_PAYLOAD",
        }

    panel = contract.get("panel") or {}

    financial_health = _score_value(
        _first_exact(panel, "financial_health", "financial_health_score", "health_score")
    )
    cash_quality = _score_value(
        _first_exact(panel, "cash_quality", "cash_quality_score")
    )
    capital_efficiency = _score_value(
        _first_exact(panel, "capital_efficiency", "capital_efficiency_score")
    )

    return {
        "status": "PASS",
        "symbol": contract.get("symbol"),
        "eligible_symbols": list(contract.get("eligible_symbols") or []),
        "panel_status": _first_exact(panel, "status"),
        "coverage_status": _first_exact(panel, "coverage_status"),
        "decision_support_status": _first_exact(panel, "decision_support_status"),
        "financial_health": financial_health,
        "cash_quality": cash_quality,
        "capital_efficiency": capital_efficiency,
        "risk": _first_exact(panel, "risk", "risk_level"),
        "current_price": _first_exact(panel, "current_price"),
        "attractive_entry_price": _first_exact(panel, "attractive_entry_price"),
        "valuation_status": _first_exact(panel, "valuation_status"),
        "panel_artifact": contract.get("panel_artifact"),
        "mode": "READ_ONLY_RENDERER_PAYLOAD",
    }


__all__ = ["build_financial_intelligence_renderer_payload"]
