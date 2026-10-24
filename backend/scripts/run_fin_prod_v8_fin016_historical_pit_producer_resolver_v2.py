from __future__ import annotations

import ast
import json
from pathlib import Path

EXCLUDED_PARTS = {
    "tests",
    "__pycache__",
}
EXCLUDED_FILES = {
    "financial_intelligence_validation.py",
    "financial_intelligence_validation_report.py",
    "run_fin_prod_v8_fin016_validation_report.py",
    "run_fin_prod_v8_fin016_historical_pit_exact_source_resolver.py",
}

TARGET_NAMES = {
    "PointInTimeObservation",
    "forward_return",
    "publication_date",
    "observation_date",
}


def constructor_calls(tree: ast.AST) -> list[dict]:
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = None
        if isinstance(node.func, ast.Name):
            fn = node.func.id
        elif isinstance(node.func, ast.Attribute):
            fn = node.func.attr
        if fn != "PointInTimeObservation":
            continue

        kw = [k.arg for k in node.keywords if k.arg]
        calls.append({
            "line": getattr(node, "lineno", None),
            "keyword_args": kw,
            "positional_arg_count": len(node.args),
        })
    return calls


def inspect_py(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        tree = ast.parse(text)
    except Exception:
        return None

    calls = constructor_calls(tree)
    low = text.lower()
    semantic = {
        "point_in_time_constructor": bool(calls),
        "forward_return": "forward_return" in low,
        "publication_date": "publication_date" in low or "published_at" in low,
        "observation_date": "observation_date" in low or "as_of" in low or "candidate_date" in low,
        "outcome_semantics": any(x in low for x in ("outcome", "future_return", "forward_return", "getiri")),
    }

    if not calls and sum(bool(v) for v in semantic.values()) < 4:
        return None

    return {
        "path": str(path),
        "constructor_calls": calls,
        "semantic": semantic,
    }


def inspect_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None

    text = json.dumps(data, ensure_ascii=False).lower()
    hits = {
        "score": '"score"' in text or '"skor"' in text,
        "forward_return": '"forward_return"' in text or '"future_return"' in text,
        "publication_date": '"publication_date"' in text or '"published_at"' in text,
        "observation_date": '"observation_date"' in text or '"as_of"' in text or '"as_of_date"' in text,
    }
    if sum(hits.values()) < 3:
        return None
    return {"path": str(path), "hits": hits}


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    backend = root / "backend"

    producers = []
    for path in backend.rglob("*.py"):
        rel_parts = set(path.relative_to(backend).parts)
        if rel_parts & EXCLUDED_PARTS:
            continue
        if path.name in EXCLUDED_FILES:
            continue
        rec = inspect_py(path)
        if rec:
            producers.append(rec)

    artifacts = []
    data_dirs = [backend / "data", backend / "app" / "history"]
    for base in data_dirs:
        if not base.exists():
            continue
        for path in base.rglob("*.json"):
            rec = inspect_json(path)
            if rec:
                artifacts.append(rec)

    exact_producers = [
        p for p in producers
        if p["constructor_calls"]
        and p["semantic"]["forward_return"]
        and p["semantic"]["publication_date"]
        and p["semantic"]["observation_date"]
    ]

    if exact_producers:
        status = "EXACT_PRODUCTION_OBSERVATION_PRODUCER_FOUND"
        primary = sorted(exact_producers, key=lambda x: x["path"])[0]["path"]
        blocker = None
    else:
        status = "NO_EXACT_PRODUCTION_OBSERVATION_PRODUCER"
        primary = None
        blocker = "HISTORICAL_PIT_OBSERVATION_PRODUCER_MISSING"

    payload = {
        "schema_version": "fin-prod-v8-fin016-historical-pit-producer-resolution-v2",
        "mode": "READ_ONLY_PRODUCER_RESOLUTION",
        "status": status,
        "primary": primary,
        "blocker": blocker,
        "rules": [
            "VALIDATOR_ONLY_MODULES_ARE_NOT_DATA_SOURCES",
            "TESTS_ARE_NOT_PRODUCTION_SOURCES",
            "POINT_IN_TIME_OBSERVATION_MUST_BE_CONSTRUCTED_FROM_REAL_EXISTING_EVIDENCE",
            "NO_SYNTHETIC_PRODUCTION_CALIBRATION",
            "NO_FUZZY_FIELD_MAPPING",
        ],
        "production_candidates": producers,
        "artifact_candidates": artifacts,
    }

    out = backend / "data/financial_intelligence/FIN_PROD_V8_FIN016_HISTORICAL_PIT_PRODUCER_RESOLUTION_V2.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("STATUS=" + status)
    print("PRIMARY=" + str(primary))
    print("BLOCKER=" + str(blocker))
    print("PRODUCTION_CANDIDATES=" + str(len(producers)))
    print("ARTIFACT_CANDIDATES=" + str(len(artifacts)))
    print("RESULT=" + str(out))
    print("FIN_PROD_V8_FIN016_HISTORICAL_PIT_PRODUCER_RESOLVER_V2=PASS")


if __name__ == "__main__":
    main()
