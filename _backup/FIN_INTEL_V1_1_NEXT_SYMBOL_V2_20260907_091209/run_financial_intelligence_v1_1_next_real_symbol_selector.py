from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

IGNORE = {
    "TUPRS", "PASS", "READY", "BLOCKED", "UNKNOWN", "TRUE", "FALSE",
    "FIN", "PROD", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8",
}
SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9]{2,7}$")

RELEVANT_NAME_TERMS = (
    "financial",
    "kap",
    "ownership",
    "investability",
    "fundamental",
    "valuation",
    "canonical",
)

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None

def exact_symbol_values(node):
    found = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "symbol" and isinstance(v, str):
                found.append(v.strip().upper())
            else:
                found.extend(exact_symbol_values(v))
    elif isinstance(node, list):
        for x in node:
            found.extend(exact_symbol_values(x))
    return found

def filename_symbols(name: str):
    stem = Path(name).stem.upper()
    tokens = re.split(r"[^A-Z0-9]+", stem)
    return [t for t in tokens if SYMBOL_RE.match(t) and t not in IGNORE]

def main():
    root = Path(__file__).resolve().parents[2]
    backend = root / "backend"
    data = backend / "data"
    out_dir = data / "financial_intelligence"

    evidence = defaultdict(lambda: {
        "files": set(),
        "json_symbol_hits": 0,
        "filename_hits": 0,
        "financial_hits": 0,
        "kap_hits": 0,
        "ownership_hits": 0,
        "investability_hits": 0,
        "valuation_hits": 0,
        "canonical_hits": 0,
    })

    files_scanned = 0
    for path in data.rglob("*"):
        if not path.is_file():
            continue
        lname = path.name.lower()
        if not any(term in lname for term in RELEVANT_NAME_TERMS):
            continue
        if path.suffix.lower() not in {".json", ".txt", ".csv", ".xls", ".xlsx"}:
            continue

        files_scanned += 1
        symbols = set(filename_symbols(path.name))

        if path.suffix.lower() == ".json":
            obj = load_json(path)
            if obj is not None:
                js = {s for s in exact_symbol_values(obj) if SYMBOL_RE.match(s) and s not in IGNORE}
                for s in js:
                    evidence[s]["json_symbol_hits"] += 1
                symbols |= js

        for sym in symbols:
            if sym == "TUPRS":
                continue
            rec = evidence[sym]
            rec["files"].add(str(path))
            rec["filename_hits"] += int(sym in filename_symbols(path.name))
            rec["financial_hits"] += int("financial" in lname or "fundamental" in lname)
            rec["kap_hits"] += int("kap" in lname)
            rec["ownership_hits"] += int("ownership" in lname)
            rec["investability_hits"] += int("investability" in lname)
            rec["valuation_hits"] += int("valuation" in lname)
            rec["canonical_hits"] += int("canonical" in lname)

    candidates = []
    for sym, rec in evidence.items():
        score = (
            5 * rec["json_symbol_hits"]
            + 3 * rec["financial_hits"]
            + 3 * rec["kap_hits"]
            + 2 * rec["ownership_hits"]
            + 2 * rec["investability_hits"]
            + 2 * rec["valuation_hits"]
            + 2 * rec["canonical_hits"]
            + min(len(rec["files"]), 10)
        )
        candidates.append({
            "symbol": sym,
            "evidence_score": score,
            "file_count": len(rec["files"]),
            "json_symbol_hits": rec["json_symbol_hits"],
            "financial_hits": rec["financial_hits"],
            "kap_hits": rec["kap_hits"],
            "ownership_hits": rec["ownership_hits"],
            "investability_hits": rec["investability_hits"],
            "valuation_hits": rec["valuation_hits"],
            "canonical_hits": rec["canonical_hits"],
            "files": sorted(rec["files"])[:30],
        })

    candidates.sort(key=lambda x: (-x["evidence_score"], -x["file_count"], x["symbol"]))

    selected = None
    for c in candidates:
        # Require at least one exact JSON symbol hit OR multiple independent files.
        if c["json_symbol_hits"] >= 1 or c["file_count"] >= 2:
            selected = c
            break

    status = "NEXT_REAL_SYMBOL_SELECTED" if selected else "NO_SAFE_NEXT_SYMBOL_IN_EXISTING_DATA"

    payload = {
        "schema_version": "financial-intelligence-v1.1-next-real-symbol-selector-v1",
        "status": status,
        "mode": "READ_ONLY_SELECTION",
        "reference_symbol": "TUPRS",
        "files_scanned": files_scanned,
        "candidate_count": len(candidates),
        "selected_symbol": selected["symbol"] if selected else None,
        "selected_evidence_score": selected["evidence_score"] if selected else None,
        "selected_file_count": selected["file_count"] if selected else 0,
        "top_candidates": candidates[:20],
        "rules": [
            "TUPRS_EXCLUDED_AS_REFERENCE",
            "NO_ARBITRARY_SYMBOL_SELECTION",
            "EXISTING_REPOSITORY_EVIDENCE_REQUIRED",
            "NO_NEW_SCORE",
            "NO_NEW_STORE",
            "NO_AL_SAT_SCANNER_RANKING_PORTFOLIO_MUTATION",
        ],
    }

    out = out_dir / "FINANCIAL_INTELLIGENCE_V1_1_NEXT_REAL_SYMBOL_SELECTION.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"STATUS={status}")
    print(f"FILES_SCANNED={files_scanned}")
    print(f"CANDIDATE_COUNT={len(candidates)}")
    print(f"SELECTED_SYMBOL={payload['selected_symbol']}")
    print(f"SELECTED_EVIDENCE_SCORE={payload['selected_evidence_score']}")
    print(f"SELECTED_FILE_COUNT={payload['selected_file_count']}")
    for c in candidates[:10]:
        print(f"CANDIDATE={c['symbol']} SCORE={c['evidence_score']} FILES={c['file_count']} JSON_HITS={c['json_symbol_hits']}")
    print(f"RESULT={out}")
    print("FINANCIAL_INTELLIGENCE_V1_1_NEXT_REAL_SYMBOL_SELECTOR=PASS")

if __name__ == "__main__":
    main()
