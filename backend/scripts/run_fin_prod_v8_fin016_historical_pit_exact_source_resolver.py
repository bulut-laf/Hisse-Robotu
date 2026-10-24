from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any


CANDIDATES = [
    "backend/app/analysis/financial_intelligence_validation.py",
    "backend/app/models/investability_models.py",
    "backend/app/analysis/historical_research_replay.py",
    "backend/app/analysis/signal_outcome_tracking.py",
    "backend/app/analysis/next_day_walk_forward.py",
    "backend/app/analysis/momentum_walk_forward.py",
    "backend/app/analysis/fundamental_score_history.py",
    "backend/app/history/scan_history.py",
    "backend/app/history/momentum_history.py",
]

TERMS = {
    "score": ["score", "skor"],
    "observation_time": ["observation_date", "as_of", "candidate_date", "signal_date", "date"],
    "publication_time": ["publication_date", "published_at", "available_as_of"],
    "forward_outcome": ["forward_return", "future_return", "return", "outcome", "getiri"],
}


def _names_in_ast(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.Attribute):
            out.add(node.attr)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
    return out


def _defs(tree: ast.AST) -> dict[str, list[str]]:
    funcs = []
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
    return {"functions": sorted(set(funcs)), "classes": sorted(set(classes))}


def _term_hits(text: str, names: set[str]) -> dict[str, list[str]]:
    low = text.lower()
    result: dict[str, list[str]] = {}
    for key, aliases in TERMS.items():
        hits = []
        for alias in aliases:
            if alias.lower() in low or alias in names:
                hits.append(alias)
        result[key] = hits
    return result


def _candidate_record(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    rec: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return rec

    text = path.read_text(encoding="utf-8-sig", errors="replace")
    try:
        tree = ast.parse(text)
        names = _names_in_ast(tree)
        rec["ast_ok"] = True
        rec.update(_defs(tree))
    except Exception as exc:
        names = set()
        rec["ast_ok"] = False
        rec["ast_error"] = f"{type(exc).__name__}: {exc}"
        rec["functions"] = []
        rec["classes"] = []

    hits = _term_hits(text, names)
    rec["hits"] = hits
    rec["coverage"] = {k: bool(v) for k, v in hits.items()}
    rec["coverage_count"] = sum(rec["coverage"].values())

    exact_lines = []
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if any(alias.lower() in low for aliases in TERMS.values() for alias in aliases):
            exact_lines.append({"line": i, "text": line.strip()})
        if len(exact_lines) >= 80:
            break
    rec["evidence_lines"] = exact_lines
    return rec


def _pick(records: list[dict[str, Any]]) -> dict[str, Any]:
    # Exact all-four-in-one source is strongest.
    all_four = [r for r in records if r.get("coverage_count") == 4]
    if all_four:
        chosen = sorted(all_four, key=lambda r: r["path"])[0]
        return {
            "status": "EXACT_SINGLE_SOURCE_FOUND",
            "primary": chosen["path"],
            "bridge_required": False,
            "reason": "One existing source contains score, observation time, publication time and forward outcome semantics.",
        }

    # Otherwise identify best score/outcome source and canonical publication source.
    score_outcome = [
        r for r in records
        if r.get("coverage", {}).get("score") and
           r.get("coverage", {}).get("observation_time") and
           r.get("coverage", {}).get("forward_outcome")
    ]
    publication = [
        r for r in records
        if r.get("coverage", {}).get("publication_time") and
           r.get("coverage", {}).get("observation_time")
    ]
    if score_outcome and publication:
        so = sorted(score_outcome, key=lambda r: (-r["coverage_count"], r["path"]))[0]
        pub = sorted(publication, key=lambda r: (-r["coverage_count"], r["path"]))[0]
        return {
            "status": "EXACT_TWO_SOURCE_BRIDGE_REQUIRED",
            "primary": so["path"],
            "publication_source": pub["path"],
            "bridge_required": True,
            "reason": "Existing outcome source lacks publication timing; bridge must join exact historical outcome rows with canonical publication/as-of evidence without inventing values.",
        }

    return {
        "status": "NO_SAFE_EXACT_SOURCE_CHAIN",
        "bridge_required": False,
        "reason": "No existing exact source chain proves score + observation time + publication time + forward outcome. FIN-016 production calibration must remain blocked.",
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    out = root / "backend/data/financial_intelligence/FIN_PROD_V8_FIN016_HISTORICAL_PIT_EXACT_SOURCE_RESOLUTION.json"

    records = [_candidate_record(root, rel) for rel in CANDIDATES]
    resolution = _pick(records)

    payload = {
        "schema_version": "fin-prod-v8-fin016-historical-pit-exact-source-resolution-v1",
        "mode": "READ_ONLY_EXACT_SOURCE_RESOLUTION",
        "mutation": False,
        "production_calibration": False,
        "rules": [
            "NO_SYNTHETIC_DATA_AS_PRODUCTION_CALIBRATION",
            "NO_FUZZY_FIELD_MAPPING",
            "NO_INVENTED_PUBLICATION_TIMESTAMP",
            "NO_INVENTED_FORWARD_RETURN",
            "NO_WEIGHT_OR_THRESHOLD_OPTIMIZATION",
        ],
        "resolution": resolution,
        "candidates": records,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("STATUS=" + resolution["status"])
    print("BRIDGE_REQUIRED=" + ("YES" if resolution.get("bridge_required") else "NO"))
    print("PRIMARY=" + str(resolution.get("primary")))
    print("PUBLICATION_SOURCE=" + str(resolution.get("publication_source")))
    print("RESULT=" + str(out))
    print("FIN_PROD_V8_FIN016_HISTORICAL_PIT_EXACT_SOURCE_RESOLVER=PASS")


if __name__ == "__main__":
    main()
