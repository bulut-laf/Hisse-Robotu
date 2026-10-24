from __future__ import annotations

from pathlib import Path
from typing import Any

from app.ui.financial_intelligence_renderer_contract import (
    build_financial_intelligence_renderer_contract,
)


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

    def first(*keys):
        for key in keys:
            value = panel.get(key)
            if value is not None:
                return value
        return None

    financial_health = first("financial_health", "financial_health_score", "health_score")
    if isinstance(financial_health, dict):
        financial_health = (
            financial_health.get("score")
            or financial_health.get("value")
            or financial_health.get("total_score")
            or financial_health.get("overall_score")
        )

    cash_quality = first("cash_quality", "cash_quality_score")
    if isinstance(cash_quality, dict):
        cash_quality = (
            cash_quality.get("score")
            or cash_quality.get("value")
            or cash_quality.get("total_score")
        )

    capital_efficiency = first("capital_efficiency", "capital_efficiency_score")
    if isinstance(capital_efficiency, dict):
        capital_efficiency = (
            capital_efficiency.get("score")
            or capital_efficiency.get("value")
            or capital_efficiency.get("total_score")
        )

    payload = {
        "status": "PASS",
        "symbol": contract.get("symbol"),
        "eligible_symbols": list(contract.get("eligible_symbols") or []),
        "panel_status": first("status"),
        "coverage_status": first("coverage_status"),
        "decision_support_status": first("decision_support_status"),
        "financial_health": financial_health,
        "cash_quality": cash_quality,
        "capital_efficiency": capital_efficiency,
        "risk": first("risk", "risk_level"),
        "current_price": first("current_price"),
        "attractive_entry_price": first("attractive_entry_price"),
        "valuation_status": first("valuation_status", "status_label"),
        "panel_artifact": contract.get("panel_artifact"),
        "mode": "READ_ONLY_RENDERER_PAYLOAD",
    }

    return payload


__all__ = ["build_financial_intelligence_renderer_payload"]
