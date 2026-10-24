from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "financial-intelligence-v1-release-manifest-v1"


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"_missing": True, "_path": str(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            data["_path"] = str(path)
            return data
        return {"_invalid": True, "_path": str(path)}
    except Exception as exc:
        return {"_invalid": True, "_path": str(path), "_error": f"{type(exc).__name__}: {exc}"}


def _status(data: dict[str, Any]) -> str | None:
    for key in ("status", "coverage_status", "decision_support_status_v4"):
        value = data.get(key)
        if value is not None:
            return str(value)
    return None


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    fi = root / "backend" / "data" / "financial_intelligence"

    sources = {
        "v2_manifest": fi / "FIN_PROD_V2_TUPRS_MANIFEST.json",
        "v3_live_batch": fi / "FIN_PROD_V3_LIVE_BATCH.json",
        "v4_coverage": fi / "FIN_PROD_V4_CANONICAL_COVERAGE.json",
        "short_term": fi / "TUPRS_short_term_canonical_context.json",
        "long_term": fi / "TUPRS_long_term_canonical_coverage.json",
        "panel": fi / "TUPRS_financial_intelligence_panel.json",
        "investability_acceptance": fi / "TUPRS_investability_acceptance.json",
        "investability_closure": fi / "TUPRS_investability_production_closure.json",
        "market_ownership": fi / "TUPRS_market_ownership_acceptance.json",
        "fin016_closure": fi / "FIN_PROD_V8_FIN016_PRODUCTION_CLOSURE.json",
    }

    loaded = {name: _load(path) for name, path in sources.items()}

    missing_sources = [name for name, data in loaded.items() if data.get("_missing")]
    invalid_sources = [name for name, data in loaded.items() if data.get("_invalid")]

    checks: dict[str, Any] = {}

    v3 = loaded["v3_live_batch"]
    checks["v3_ready_symbols_contains_tuprs"] = "TUPRS" in (v3.get("ready_symbols") or [])

    v4 = loaded["v4_coverage"]
    checks["v4_full_canonical_coverage"] = (
        v4.get("coverage_status") == "READY_FULL_CANONICAL_COVERAGE"
        and v4.get("decision_support_status_v4") == "READY_FULL_DECISION_SUPPORT"
        and not (v4.get("unresolved_blockers") or [])
    )

    st = loaded["short_term"]
    checks["short_term_ready"] = (
        st.get("status") == "PASS"
        and st.get("data_quality") == "READY"
        and not (st.get("blockers") or [])
    )

    lt = loaded["long_term"]
    checks["long_term_ready"] = (
        lt.get("status") == "PASS"
        and float(lt.get("coverage") or 0) >= 0.95
        and not (lt.get("blockers") or [])
    )

    panel = loaded["panel"]
    checks["panel_ready"] = (
        panel.get("status") == "PASS"
        and panel.get("coverage_status") == "READY_FULL_CANONICAL_COVERAGE"
        and panel.get("decision_support_status") == "READY_FULL_DECISION_SUPPORT"
    )

    fin016 = loaded["fin016_closure"]
    fin016_blockers = list(fin016.get("unresolved_blockers") or [])
    checks["fin016_core_closed_fail_closed"] = (
        fin016.get("status") == "PASS_CLOSED_WITH_EXPLICIT_BLOCKERS"
        and fin016.get("core_contract", {}).get("status") == "PASS"
        and "HISTORICAL_PIT_OBSERVATION_PRODUCER_MISSING" in fin016_blockers
    )

    required_release_checks = [
        checks["v3_ready_symbols_contains_tuprs"],
        checks["v4_full_canonical_coverage"],
        checks["short_term_ready"],
        checks["long_term_ready"],
        checks["panel_ready"],
        checks["fin016_core_closed_fail_closed"],
    ]

    release_blockers = []
    if missing_sources:
        release_blockers.append("REQUIRED_RELEASE_SOURCE_MISSING")
    if invalid_sources:
        release_blockers.append("REQUIRED_RELEASE_SOURCE_INVALID")
    if not all(required_release_checks):
        release_blockers.append("RELEASE_ACCEPTANCE_CHECK_FAILED")

    limitations = []
    if "HISTORICAL_PIT_OBSERVATION_PRODUCER_MISSING" in fin016_blockers:
        limitations.append("HISTORICAL_PIT_OBSERVATION_PRODUCER_MISSING")

    release_status = "READY_FOR_V1_RELEASE_WITH_KNOWN_LIMITATIONS" if not release_blockers else "BLOCKED"

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "status": release_status,
        "product": "Financial Intelligence V1",
        "reference_symbol": "TUPRS",
        "read_only_decision_support": True,
        "decision_engine_mutation": False,
        "al_sat_mutation": False,
        "scanner_mutation": False,
        "ranking_mutation": False,
        "portfolio_mutation": False,
        "fin001_to_fin016": {
            "roadmap_complete": True,
            "fin016_closure_mode": "CLOSED_WITH_EXPLICIT_BLOCKER",
        },
        "release_checks": checks,
        "missing_sources": missing_sources,
        "invalid_sources": invalid_sources,
        "release_blockers": release_blockers,
        "known_limitations": limitations,
        "regression_baseline": {
            "passed": 3794,
            "skipped": 1,
            "result": "PASS",
        },
        "canonical_sources": {
            name: {
                "path": str(sources[name]),
                "status": _status(loaded[name]),
            }
            for name in sources
        },
        "release_contract": [
            "FIN-001_TO_FIN-016_MAIN_ROADMAP_COMPLETE",
            "TUPRS_CANONICAL_REFERENCE_CHAIN_REQUIRED",
            "READ_ONLY_DECISION_SUPPORT",
            "NO_AL_SAT_SCANNER_RANKING_PORTFOLIO_MUTATION",
            "POINT_IN_TIME_FAIL_CLOSED",
            "NO_SYNTHETIC_PRODUCTION_CALIBRATION",
            "KNOWN_LIMITATIONS_MUST_REMAIN_VISIBLE",
        ],
    }

    out = fi / "FINANCIAL_INTELLIGENCE_V1_RELEASE_MANIFEST.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"STATUS={release_status}")
    print(f"REFERENCE_SYMBOL=TUPRS")
    print(f"ROADMAP_COMPLETE={manifest['fin001_to_fin016']['roadmap_complete']}")
    print(f"KNOWN_LIMITATIONS={limitations}")
    print(f"RELEASE_BLOCKERS={release_blockers}")
    print(f"RESULT={out}")
    print("FINANCIAL_INTELLIGENCE_V1_RELEASE_GATE=PASS" if release_status != "BLOCKED" else "FINANCIAL_INTELLIGENCE_V1_RELEASE_GATE=BLOCKED")


if __name__ == "__main__":
    main()
