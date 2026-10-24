from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.ui.financial_intelligence_renderer_contract import (
    build_financial_intelligence_renderer_contract,
)


CASH_COMPONENT_NAMES = {
    "CASH_QUALITY",
    "EARNINGS_CASH_QUALITY",
    "EARNINGS_AND_CASH_QUALITY",
    "EARNINGS_QUALITY",
}

VALUATION_LABELS = {
    "VERY_CHEAP",
    "CHEAP",
    "ATTRACTIVE",
    "FAIR",
    "EXPENSIVE",
    "VERY_EXPENSIVE",
    "OVERVALUED",
    "UNDERVALUED",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _norm(value: Any) -> str:
    return str(value).strip().upper().replace(" ", "_").replace("-", "_")


def _as_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _score_from_obj(obj: Any) -> float | None:
    if isinstance(obj, dict):
        for key in ("score", "value", "total_score", "overall_score"):
            if key in obj:
                n = _as_number(obj[key])
                if n is not None:
                    return n
    return _as_number(obj)


def _find_component_score(node: Any, component_names: set[str]) -> float | None:
    if isinstance(node, dict):
        # Key-as-component contract.
        for key, value in node.items():
            if _norm(key) in component_names:
                score = _score_from_obj(value)
                if score is not None:
                    return score

        # Object-with-component-identity contract.
        identity = None
        for key in ("component", "component_name", "name", "id", "key", "metric"):
            value = node.get(key)
            if isinstance(value, str) and _norm(value) in component_names:
                identity = _norm(value)
                break

        if identity:
            score = _score_from_obj(node)
            if score is not None:
                return score

        for value in node.values():
            found = _find_component_score(value, component_names)
            if found is not None:
                return found

    elif isinstance(node, list):
        for item in node:
            found = _find_component_score(item, component_names)
            if found is not None:
                return found

    return None


def _find_exact_number(node: Any, keys: tuple[str, ...]) -> float | None:
    if isinstance(node, dict):
        for key in keys:
            if key in node:
                n = _score_from_obj(node[key])
                if n is not None:
                    return n
        for value in node.values():
            found = _find_exact_number(value, keys)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_exact_number(item, keys)
            if found is not None:
                return found
    return None


def _find_exact_text(node: Any, keys: tuple[str, ...]) -> str | None:
    if isinstance(node, dict):
        for key in keys:
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for value in node.values():
            found = _find_exact_text(value, keys)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_exact_text(item, keys)
            if found is not None:
                return found
    return None


def _find_valuation_status(node: Any) -> str | None:
    if isinstance(node, dict):
        # Explicit semantic keys are always valid.
        for key in (
            "valuation_status",
            "margin_of_safety_status",
            "valuation_label",
            "price_status",
        ):
            value = node.get(key)
            if isinstance(value, str) and _norm(value) in VALUATION_LABELS:
                return _norm(value)

        # Context object named margin_of_safety / valuation may carry generic status.
        for context_key in ("margin_of_safety", "valuation", "valuation_summary"):
            context = node.get(context_key)
            if isinstance(context, dict):
                for key in ("status", "label", "classification"):
                    value = context.get(key)
                    if isinstance(value, str) and _norm(value) in VALUATION_LABELS:
                        return _norm(value)
                found = _find_valuation_status(context)
                if found is not None:
                    return found

        # Generic status is accepted only if THIS SAME object has valuation evidence
        # and the value is a valuation classification, never PASS/FAIL.
        evidence_keys = {
            "current_price",
            "attractive_entry_price",
            "margin_of_safety",
            "required_margin_of_safety",
            "fair_value",
            "base_fair_value",
        }
        if any(key in node for key in evidence_keys):
            for key in ("status", "label", "classification"):
                value = node.get(key)
                if isinstance(value, str) and _norm(value) in VALUATION_LABELS:
                    return _norm(value)

        for value in node.values():
            found = _find_valuation_status(value)
            if found is not None:
                return found

    elif isinstance(node, list):
        for item in node:
            found = _find_valuation_status(item)
            if found is not None:
                return found

    return None


def _acceptance_file(data_dir: Path, symbol: str) -> Path | None:
    files = sorted(data_dir.glob(f"financial_intelligence_acceptance_{symbol}_*.json"))
    return files[-1] if files else None


def _candidate_jsons(fi_dir: Path, symbol: str) -> list[Path]:
    preferred_patterns = (
        f"{symbol}*cash*.json",
        f"{symbol}*quality*.json",
        f"{symbol}*valuation*.json",
        f"{symbol}*fair_value*.json",
        f"{symbol}*margin*.json",
        f"{symbol}_financial_intelligence_panel.json",
    )
    found = []
    seen = set()
    for pattern in preferred_patterns:
        for path in sorted(fi_dir.glob(pattern)):
            if str(path) not in seen:
                seen.add(str(path))
                found.append(path)
    return found


def _bank_production_section(
    panel: Any,
) -> dict[str, Any] | None:
    if not isinstance(panel, dict):
        return None

    sections = panel.get("sections")

    if not isinstance(sections, dict):
        return None

    bank = sections.get("bank_production")

    if not isinstance(bank, dict):
        return None

    if bank.get("activation_ready") is not True:
        return None

    if bank.get("production_evidence") is not True:
        return None

    return {
        "status": bank.get("status"),
        "symbol": bank.get("symbol"),
        "as_of": bank.get("as_of"),
        "publication_date": bank.get("publication_date"),
        "production_evidence": True,
        "activation_ready": True,
        "read_only": True,
    }

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
            "panel_status": None,
            "financial_health": None,
            "cash_quality": None,
            "cash_quality_source": None,
            "capital_efficiency": None,
            "risk": None,
            "current_price": None,
            "attractive_entry_price": None,
            "valuation_status": None,
            "valuation_status_source": None,
            "panel_artifact": contract.get("panel_artifact"),
            "acceptance_artifact": None,
            "mode": "READ_ONLY_RENDERER_PAYLOAD",
        }

    resolved = str(contract.get("symbol"))
    panel = contract.get("panel") or {}
    panel_path = Path(contract["panel_artifact"])

    acceptance_path = _acceptance_file(data_dir, resolved)
    acceptance = _load(acceptance_path) if acceptance_path else {}

    financial_health = _find_exact_number(
        acceptance,
        ("financial_health_score", "health_score"),
    )
    if financial_health is None:
        financial_health = _find_exact_number(
            panel,
            ("financial_health_score", "health_score", "financial_health"),
        )

    cash_quality = _find_component_score(acceptance, CASH_COMPONENT_NAMES)
    cash_source = str(acceptance_path) if cash_quality is not None and acceptance_path else None

    candidates = _candidate_jsons(fi_dir, resolved)
    if cash_quality is None:
        for path in candidates:
            try:
                obj = _load(path)
            except Exception:
                continue
            value = _find_component_score(obj, CASH_COMPONENT_NAMES)
            if value is not None:
                cash_quality = value
                cash_source = str(path)
                break

    capital_efficiency = _find_exact_number(
        panel,
        ("capital_efficiency_score", "capital_efficiency"),
    )

    risk = _find_exact_text(
        acceptance,
        ("risk_level", "financial_risk_level", "deterioration_risk_level"),
    )
    if risk is None:
        risk = _find_exact_text(
            panel,
            ("risk_level", "financial_risk_level", "deterioration_risk_level"),
        )

    current_price = _find_exact_number(panel, ("current_price",))
    attractive_entry_price = _find_exact_number(panel, ("attractive_entry_price",))

    valuation_status = _find_valuation_status(panel)
    valuation_status_source = str(panel_path) if valuation_status else None

    if valuation_status is None:
        for path in candidates:
            try:
                obj = _load(path)
            except Exception:
                continue
            value = _find_valuation_status(obj)
            if value is not None:
                valuation_status = value
                valuation_status_source = str(path)
                break

    bank_production = _bank_production_section(panel)

    return {
        "status": "PASS",
        "symbol": resolved,
        "eligible_symbols": list(contract.get("eligible_symbols") or []),
        "panel_status": _find_exact_text(panel, ("status",)),
        "financial_health": financial_health,
        "cash_quality": cash_quality,
        "cash_quality_source": cash_source,
        "capital_efficiency": capital_efficiency,
        "risk": risk,
        "current_price": current_price,
        "attractive_entry_price": attractive_entry_price,
        "valuation_status": valuation_status,
        "valuation_status_source": valuation_status_source,
        "bank_production": bank_production,
        "panel_artifact": str(panel_path),
        "acceptance_artifact": str(acceptance_path) if acceptance_path else None,
        "mode": "READ_ONLY_RENDERER_PAYLOAD",
    }


__all__ = ["build_financial_intelligence_renderer_payload"]
