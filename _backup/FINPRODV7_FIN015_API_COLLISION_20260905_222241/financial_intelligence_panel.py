
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json


SCHEMA_VERSION = "fin-prod-v7-financial-intelligence-panel-v1"
MODE = "READ_ONLY_FINANCIAL_INTELLIGENCE_PANEL_V1"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _pick(obj: Any, *path: str) -> Any:
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _find_component(payload: dict[str, Any] | None, code: str) -> Any:
    if not isinstance(payload, dict):
        return None
    health = payload.get("financial_health") or {}
    components = health.get("components") or []
    if isinstance(components, dict):
        item = components.get(code)
        if isinstance(item, dict):
            return item.get("score")
        return item
    for item in components:
        if isinstance(item, dict) and str(item.get("code") or "").upper() == code.upper():
            return item.get("score")
    return None


def _find_metric(payload: dict[str, Any] | None, code: str) -> Any:
    if not isinstance(payload, dict):
        return None
    for section_name in ("financial_health", "earnings_cash_quality", "financial_risk"):
        section = payload.get(section_name) or {}
        metrics = section.get("metrics") or []
        for item in metrics:
            if isinstance(item, dict) and str(item.get("code") or "").upper() == code.upper():
                return item.get("value")
    return None


def _status(obj: Any) -> Any:
    if isinstance(obj, dict):
        return obj.get("status")
    return obj


def _value(obj: Any, *keys: str) -> Any:
    if not isinstance(obj, dict):
        return None
    for key in keys:
        if key in obj:
            return obj.get(key)
    return None


def _first(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def build_financial_intelligence_panel(
    project_root: str | Path,
    symbol: str,
    *,
    period_key: str = "2026_2",
) -> dict[str, Any]:
    root = Path(project_root)
    backend = root / "backend"
    fi = backend / "data" / "financial_intelligence"
    symbol = symbol.strip().upper()

    financial_core_path = backend / "data" / f"financial_intelligence_acceptance_{symbol}_{period_key}.json"
    market_path = fi / f"{symbol}_market_ownership_acceptance.json"
    fair_path = fi / f"{symbol}_fair_value_acceptance.json"
    investability_path = fi / f"{symbol}_investability_production_closure.json"
    short_path = fi / f"{symbol}_short_term_canonical_context.json"
    long_path = fi / f"{symbol}_long_term_canonical_coverage.json"
    v4_path = fi / "FIN_PROD_V4_CANONICAL_COVERAGE.json"

    financial_core = _load(financial_core_path)
    market = _load(market_path)
    fair = _load(fair_path)
    investability = _load(investability_path)
    short = _load(short_path)
    long = _load(long_path)
    v4 = _load(v4_path)

    v4_symbol = None
    if isinstance(v4, dict):
        for item in v4.get("symbols") or []:
            if isinstance(item, dict) and str(item.get("symbol") or "").upper() == symbol:
                v4_symbol = item
                break

    canonical_coverage = _pick(v4_symbol, "canonical_coverage_v4") if v4_symbol else None

    health_score = _first(
        _pick(financial_core, "financial_health", "total_score"),
        _pick(financial_core, "financial_health", "score"),
        _pick(investability, "long_term", "components", "FINANCIAL_HEALTH", "score"),
    )

    cash_quality_score = _first(
        _pick(financial_core, "earnings_cash_quality", "total_score"),
        _pick(financial_core, "earnings_cash_quality", "score"),
        _pick(investability, "long_term", "components", "CASH_QUALITY", "score"),
    )

    risk_status = _first(
        _pick(financial_core, "financial_risk", "risk_level"),
        _pick(financial_core, "financial_risk", "status"),
        _pick(financial_core, "risk", "level"),
        _pick(financial_core, "risk", "status"),
    )

    capital_efficiency = _first(
        _find_component(financial_core, "CAPITAL_EFFICIENCY"),
        _pick(long, "capital_efficiency", "value"),
        _pick(investability, "long_term", "components", "CAPITAL_EFFICIENCY", "score"),
    )

    fair_value_base = _first(
        _pick(fair, "composite_fair_value", "base"),
        _pick(fair, "fair_value", "base"),
        fair.get("base") if isinstance(fair, dict) else None,
    )
    fair_value_bear = _first(
        _pick(fair, "composite_fair_value", "bear"),
        _pick(fair, "fair_value", "bear"),
        fair.get("bear") if isinstance(fair, dict) else None,
    )
    fair_value_bull = _first(
        _pick(fair, "composite_fair_value", "bull"),
        _pick(fair, "fair_value", "bull"),
        fair.get("bull") if isinstance(fair, dict) else None,
    )

    current_price = _first(
        _pick(fair, "market", "current_price"),
        fair.get("current_price") if isinstance(fair, dict) else None,
        _pick(market, "market", "price"),
        _pick(market, "price", "value"),
    )

    margin_of_safety = _first(
        _pick(fair, "margin_of_safety", "current"),
        fair.get("current_margin_of_safety") if isinstance(fair, dict) else None,
        _pick(investability, "long_term", "components", "MARGIN_OF_SAFETY", "score"),
    )

    attractive_entry = _first(
        _pick(fair, "margin_of_safety", "attractive_entry_price"),
        fair.get("attractive_entry_price") if isinstance(fair, dict) else None,
    )

    valuation_status = _first(
        _pick(fair, "margin_of_safety", "status"),
        fair.get("status") if isinstance(fair, dict) else None,
        _pick(fair, "valuation", "status"),
    )

    short_status = _status(short)
    long_status = _status(long)

    business_quality = _value(long.get("business_quality") if isinstance(long, dict) else None, "value", "score")
    governance = _value(long.get("governance") if isinstance(long, dict) else None, "value", "score")
    growth = _first(
        _value(long.get("growth_context") if isinstance(long, dict) else None, "growth_durability", "value", "score"),
        _pick(investability, "long_term", "components", "GROWTH_DURABILITY", "score"),
    )

    coverage_status = _pick(canonical_coverage, "coverage_status")
    unresolved = _pick(canonical_coverage, "unresolved_blockers")
    decision_support = _first(
        _pick(v4_symbol, "decision_support_status_v4") if v4_symbol else None,
        _pick(v4_symbol, "decision_support_status") if v4_symbol else None,
    )

    missing_sources = []
    for name, path, payload in (
        ("financial_core", financial_core_path, financial_core),
        ("market_ownership", market_path, market),
        ("fair_value", fair_path, fair),
        ("investability", investability_path, investability),
        ("short_term", short_path, short),
        ("long_term", long_path, long),
        ("canonical_coverage_v4", v4_path, v4),
    ):
        if payload is None:
            missing_sources.append({"source": name, "path": str(path)})

    panel = {
        "status": "PASS" if not missing_sources else "PARTIAL",
        "mode": MODE,
        "schema_version": SCHEMA_VERSION,
        "symbol": symbol,
        "read_only": True,
        "sections": {
            "financial_health": {
                "score": health_score,
                "cash_quality_score": cash_quality_score,
                "capital_efficiency_score": capital_efficiency,
                "risk_status": risk_status,
            },
            "valuation": {
                "bear": fair_value_bear,
                "base": fair_value_base,
                "bull": fair_value_bull,
                "current_price": current_price,
                "margin_of_safety": margin_of_safety,
                "attractive_entry_price": attractive_entry,
                "status": valuation_status,
            },
            "short_term_context": {
                "status": short_status,
                "as_of_date": short.get("as_of_date") if isinstance(short, dict) else None,
                "technical_trend": short.get("technical_trend") if isinstance(short, dict) else None,
                "relative_strength": short.get("relative_strength") if isinstance(short, dict) else None,
                "volume_liquidity": short.get("volume_liquidity") if isinstance(short, dict) else None,
                "data_quality": short.get("data_quality") if isinstance(short, dict) else None,
                "blockers": short.get("blockers") if isinstance(short, dict) else None,
                "warnings": short.get("warnings") if isinstance(short, dict) else None,
            },
            "long_term_context": {
                "status": long_status,
                "as_of_date": long.get("as_of_date") if isinstance(long, dict) else None,
                "business_quality": business_quality,
                "governance": governance,
                "growth_durability": growth,
                "capital_efficiency": capital_efficiency,
                "coverage": long.get("coverage") if isinstance(long, dict) else None,
                "data_quality": long.get("data_quality") if isinstance(long, dict) else None,
                "blockers": long.get("blockers") if isinstance(long, dict) else None,
                "warnings": long.get("warnings") if isinstance(long, dict) else None,
            },
            "coverage_readiness": {
                "short_term": _pick(canonical_coverage, "short_term"),
                "long_term": _pick(canonical_coverage, "long_term"),
                "unresolved_blockers": unresolved,
                "coverage_status": coverage_status,
                "decision_support_status": decision_support,
            },
        },
        "source_health": {
            "missing_sources": missing_sources,
            "complete": not missing_sources,
        },
        "production_rules": [
            "Read-only aggregation only.",
            "No AL/SAT, scanner, ranking or portfolio mutation.",
            "Missing values remain null; they are never converted to zero.",
            "Panel readiness is a data-coverage state, not a trade recommendation.",
        ],
    }
    return panel


def save_financial_intelligence_panel(
    project_root: str | Path,
    symbol: str,
    *,
    period_key: str = "2026_2",
) -> Path:
    root = Path(project_root)
    out = root / "backend" / "data" / "financial_intelligence" / f"{symbol.upper()}_financial_intelligence_panel.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = build_financial_intelligence_panel(root, symbol, period_key=period_key)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
