from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_PANEL_STATUS = "PASS"
READY_COVERAGE = "READY_FULL_CANONICAL_COVERAGE"
READY_DECISION = "READY_FULL_DECISION_SUPPORT"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _exact_first(node: Any, key: str):
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for value in node.values():
            found = _exact_first(value, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _exact_first(item, key)
            if found is not None:
                return found
    return None


def _symbol_from_panel_name(path: Path) -> str | None:
    suffix = "_financial_intelligence_panel.json"
    if not path.name.endswith(suffix):
        return None
    symbol = path.name[:-len(suffix)].strip().upper()
    return symbol or None


def _build_entry(path: Path) -> dict[str, Any] | None:
    symbol = _symbol_from_panel_name(path)
    if not symbol:
        return None

    data = _load(path)

    status = _exact_first(data, "status")
    coverage = _exact_first(data, "coverage_status")
    decision = _exact_first(data, "decision_support_status")

    # Preserve compatibility with V4/read-model naming.
    if coverage is None:
        coverage = _exact_first(data, "coverage")
        if isinstance(coverage, dict):
            coverage = (
                coverage.get("status")
                or coverage.get("coverage_status")
                or coverage.get("decision_support_status")
            )

    if decision is None:
        decision = _exact_first(data, "decision_support")

    health = _exact_first(data, "financial_health")
    if isinstance(health, dict):
        health = (
            health.get("score")
            or health.get("value")
            or health.get("total_score")
            or health.get("overall_score")
        )

    cash_quality = _exact_first(data, "cash_quality")
    if isinstance(cash_quality, dict):
        cash_quality = (
            cash_quality.get("score")
            or cash_quality.get("value")
            or cash_quality.get("total_score")
        )

    release_ready = (
        status == REQUIRED_PANEL_STATUS
        and coverage == READY_COVERAGE
        and decision == READY_DECISION
    )

    return {
        "symbol": symbol,
        "panel_status": status,
        "coverage_status": coverage,
        "decision_support_status": decision,
        "financial_health": health,
        "cash_quality": cash_quality,
        "release_ready": release_ready,
        "panel_artifact": str(path),
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    fi = root / "backend" / "data" / "financial_intelligence"

    entries = []
    rejected = []

    for path in sorted(fi.glob("*_financial_intelligence_panel.json")):
        try:
            entry = _build_entry(path)
        except Exception as exc:
            rejected.append({
                "artifact": str(path),
                "reason": f"INVALID_PANEL:{type(exc).__name__}",
            })
            continue

        if entry is None:
            continue

        entries.append(entry)

    entries.sort(key=lambda x: x["symbol"])

    ready = [x for x in entries if x["release_ready"]]
    not_ready = [x for x in entries if not x["release_ready"]]

    payload = {
        "schema_version": "financial-intelligence-v1-1-multi-symbol-registry-v1",
        "status": "PASS",
        "mode": "READ_ONLY_REGISTRY",
        "symbol_count": len(entries),
        "release_ready_symbol_count": len(ready),
        "not_ready_symbol_count": len(not_ready),
        "symbols": entries,
        "release_ready_symbols": [x["symbol"] for x in ready],
        "not_ready_symbols": [x["symbol"] for x in not_ready],
        "rejected_artifacts": rejected,
        "rules": [
            "REGISTRY_IS_READ_ONLY",
            "NO_SYNTHETIC_SYMBOLS",
            "PANEL_ARTIFACT_REQUIRED",
            "RELEASE_READY_REQUIRES_PANEL_PASS",
            "RELEASE_READY_REQUIRES_FULL_CANONICAL_COVERAGE",
            "RELEASE_READY_REQUIRES_FULL_DECISION_SUPPORT",
            "NO_AL_SAT_SCANNER_RANKING_PORTFOLIO_MUTATION",
        ],
    }

    out = fi / "FINANCIAL_INTELLIGENCE_V1_1_MULTI_SYMBOL_REGISTRY.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("STATUS=PASS")
    print(f"SYMBOL_COUNT={payload['symbol_count']}")
    print(f"RELEASE_READY_SYMBOL_COUNT={payload['release_ready_symbol_count']}")
    print(f"RELEASE_READY_SYMBOLS={payload['release_ready_symbols']}")
    print(f"NOT_READY_SYMBOLS={payload['not_ready_symbols']}")
    print(f"REJECTED_ARTIFACT_COUNT={len(rejected)}")
    print(f"RESULT={out}")
    print("FINANCIAL_INTELLIGENCE_V1_1_MULTI_SYMBOL_REGISTRY=PASS")


if __name__ == "__main__":
    main()
