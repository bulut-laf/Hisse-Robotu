from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.ui.financial_intelligence_renderer_contract import (
    build_financial_intelligence_renderer_contract,
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def _scalar(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("score", "value", "total_score", "overall_score"):
            if key in value and value[key] is not None:
                return value[key]
        return None
    return value


def _first_scalar(node: Any, *keys: str) -> Any:
    for key in keys:
        for value in _exact_values(node, key):
            parsed = _scalar(value)
            if parsed is not None:
                return parsed
    return None


def _first_text(node: Any, *keys: str) -> str | None:
    for key in keys:
        for value in _exact_values(node, key):
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _acceptance_file(data_dir: Path, symbol: str) -> Path | None:
    files = sorted(data_dir.glob(f"financial_intelligence_acceptance_{symbol}_*.json"))
    return files[-1] if files else None


def _valuation_sources(fi_dir: Path, symbol: str) -> list[Path]:
    candidates = []
    for pattern in (
        f"{symbol}*valuation*.json",
        f"{symbol}*fair_value*.json",
        f"{symbol}*margin_of_safety*.json",
        f"{symbol}_financial_intelligence_panel.json",
    ):
        candidates.extend(sorted(fi_dir.glob(pattern)))

    # deterministic unique order
    seen = set()
    out = []
    for p in candidates:
        s = str(p)
        if s not in seen:
            seen.add(s)
            out.append(p)
    return out


def _resolve_from_sources(paths: list[Path], resolver) -> tuple[Any, str | None]:
    for path in paths:
        if not path.exists():
            continue
        try:
            obj = _load(path)
        except Exception:
            continue
        value = resolver(obj)
        if value is not None:
            return value, str(path)
    return None, None


def build_financial_intelligence_renderer_payload(
    project_root: str | Path,
    *,
    symbol: str | None = None,
) -> dict[str, Any]:
    root = Path(project_root)
    backend = root / "backend"
    data_dir = backend / "data"
    fi_dir = data_dir / "financial_intelligence"

    contract = build_financial_intelligence_renderer_contract(root, symbol=symbol)

    if contract.get("status") != "PASS":
        return {
            "status": contract.get("status"),
            "symbol": contract.get("symbol"),
            "eligible_symbols": list(contract.get("eligible_symbols") or []),
            "mode": "READ_ONLY_RENDERER_PAYLOAD",
        }

    resolved = str(contract.get("symbol"))
    panel = contract.get("panel") or {}
    panel_path = Path(contract["panel_artifact"])

    acceptance_path = _acceptance_file(data_dir, resolved)
    acceptance = _load(acceptance_path) if acceptance_path else {}

    # Financial Health: exact score aliases only.
    financial_health = _first_scalar(
        acceptance, "financial_health_score", "health_score"
    )
    if financial_health is None:
        financial_health = _first_scalar(
            panel, "financial_health_score", "health_score", "financial_health"
        )

    # Cash quality: acceptance artifact is authoritative. Do NOT accept generic
    # cash_quality because that key can represent ratios/thresholds.
    cash_quality = _first_scalar(
        acceptance,
        "cash_quality_score",
        "earnings_cash_quality_score",
        "earnings_and_cash_quality_score",
    )

    # Risk: acceptance artifact first; only explicit level/status text aliases.
    risk = _first_text(
        acceptance,
        "risk_level",
        "financial_risk_level",
        "deterioration_risk_level",
    )
    if risk is None:
        risk = _first_text(
            panel,
            "risk_level",
            "financial_risk_level",
            "deterioration_risk_level",
        )

    capital_efficiency = _first_scalar(
        panel,
        "capital_efficiency_score",
        "capital_efficiency",
    )

    current_price = _first_scalar(panel, "current_price")
    attractive_entry_price = _first_scalar(panel, "attractive_entry_price")

    valuation_paths = _valuation_sources(fi_dir, resolved)

    valuation_status, valuation_status_source = _resolve_from_sources(
        valuation_paths,
        lambda obj: _first_text(
            obj,
            "valuation_status",
            "margin_of_safety_status",
            "valuation_label",
        ),
    )

    # If dedicated valuation artifacts encode the classification as generic
    # `status`, accept it only when the same object also contains valuation evidence.
    if valuation_status is None:
        def semantic_valuation_status(obj: Any) -> str | None:
            if not isinstance(obj, dict):
                return None

            evidence_keys = {
                "current_price",
                "attractive_entry_price",
                "margin_of_safety",
                "fair_value",
                "base_fair_value",
            }

            if any(k in obj for k in evidence_keys):
                status = obj.get("status")
                if isinstance(status, str) and status.strip():
                    return status.strip()

            for value in obj.values():
                found = semantic_valuation_status(value)
                if found is not None:
                    return found
            return None

        valuation_status, valuation_status_source = _resolve_from_sources(
            valuation_paths, semantic_valuation_status
        )

    payload = {
        "status": "PASS",
        "symbol": resolved,
        "eligible_symbols": list(contract.get("eligible_symbols") or []),
        "panel_status": _first_text(panel, "status"),
        "financial_health": financial_health,
        "cash_quality": cash_quality,
        "capital_efficiency": capital_efficiency,
        "risk": risk,
        "current_price": current_price,
        "attractive_entry_price": attractive_entry_price,
        "valuation_status": valuation_status,
        "panel_artifact": str(panel_path),
        "acceptance_artifact": str(acceptance_path) if acceptance_path else None,
        "valuation_status_source": valuation_status_source,
        "mode": "READ_ONLY_RENDERER_PAYLOAD",
    }

    return payload


__all__ = ["build_financial_intelligence_renderer_payload"]
