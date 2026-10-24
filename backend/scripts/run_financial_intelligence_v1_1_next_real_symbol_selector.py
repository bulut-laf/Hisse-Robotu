from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9]{2,7}$")
ACCEPTANCE_RE = re.compile(
    r"^financial_intelligence_acceptance_(?P<symbol>[A-Z0-9.-]+)_(?P<year>\d{4})_(?P<period>[^.]+)\.json$"
)

def load_json(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, (dict, list)) else None
    except Exception:
        return None

def collect_exact_symbol_fields(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "symbol" and isinstance(v, str):
                s = v.strip().upper()
                if SYMBOL_RE.fullmatch(s):
                    out.add(s)
            collect_exact_symbol_fields(v, out)
    elif isinstance(node, list):
        for item in node:
            collect_exact_symbol_fields(item, out)

def main():
    root = Path(__file__).resolve().parents[2]
    backend = root / "backend"
    data_dir = backend / "data"
    fi_dir = data_dir / "financial_intelligence"

    evidence = defaultdict(lambda: {
        "acceptance_files": set(),
        "json_symbol_files": set(),
        "canonical_files": set(),
    })

    scanned_json = 0

    # 1) Exact acceptance filename contract.
    for path in data_dir.glob("financial_intelligence_acceptance_*.json"):
        m = ACCEPTANCE_RE.match(path.name)
        if not m:
            continue
        sym = m.group("symbol").upper()
        if SYMBOL_RE.fullmatch(sym):
            evidence[sym]["acceptance_files"].add(str(path))

    # 2) Exact JSON key "symbol" only.
    for path in data_dir.rglob("*.json"):
        scanned_json += 1
        obj = load_json(path)
        if obj is None:
            continue
        syms = set()
        collect_exact_symbol_fields(obj, syms)
        for sym in syms:
            evidence[sym]["json_symbol_files"].add(str(path))

    # 3) Existing canonical FI artifacts with exact prefix contract <SYMBOL>_...
    canonical_suffixes = (
        "_short_term_canonical_context.json",
        "_long_term_canonical_coverage.json",
        "_financial_intelligence_panel.json",
        "_market_ownership_acceptance.json",
        "_investability_acceptance.json",
        "_investability_production_closure.json",
    )
    if fi_dir.exists():
        for path in fi_dir.glob("*.json"):
            for suffix in canonical_suffixes:
                if path.name.endswith(suffix):
                    sym = path.name[:-len(suffix)].upper()
                    if SYMBOL_RE.fullmatch(sym):
                        evidence[sym]["canonical_files"].add(str(path))
                    break

    candidates = []
    for sym, rec in evidence.items():
        if sym == "TUPRS":
            continue

        acceptance_count = len(rec["acceptance_files"])
        json_count = len(rec["json_symbol_files"])
        canonical_count = len(rec["canonical_files"])

        # Exact-evidence score only; no filename token heuristics.
        score = acceptance_count * 10 + canonical_count * 5 + min(json_count, 10)

        candidates.append({
            "symbol": sym,
            "evidence_score": score,
            "acceptance_file_count": acceptance_count,
            "json_symbol_file_count": json_count,
            "canonical_file_count": canonical_count,
            "acceptance_files": sorted(rec["acceptance_files"])[:20],
            "json_symbol_files": sorted(rec["json_symbol_files"])[:20],
            "canonical_files": sorted(rec["canonical_files"])[:20],
        })

    candidates.sort(
        key=lambda x: (
            -x["acceptance_file_count"],
            -x["canonical_file_count"],
            -x["json_symbol_file_count"],
            x["symbol"],
        )
    )

    selected = None
    for c in candidates:
        # For actual rollout, require an exact FI acceptance file.
        if c["acceptance_file_count"] >= 1:
            selected = c
            break

    status = "NEXT_REAL_SYMBOL_SELECTED" if selected else "NO_SAFE_NEXT_SYMBOL_IN_EXISTING_DATA"

    payload = {
        "schema_version": "financial-intelligence-v1.1-next-real-symbol-selector-v2",
        "status": status,
        "mode": "READ_ONLY_EXACT_SYMBOL_SELECTION",
        "reference_symbol": "TUPRS",
        "scanned_json_files": scanned_json,
        "candidate_count": len(candidates),
        "selected_symbol": selected["symbol"] if selected else None,
        "selected_evidence_score": selected["evidence_score"] if selected else None,
        "selected_acceptance_file_count": selected["acceptance_file_count"] if selected else 0,
        "top_candidates": candidates[:20],
        "rules": [
            "EXACT_JSON_SYMBOL_FIELD_ONLY",
            "EXACT_ACCEPTANCE_FILENAME_CONTRACT_ONLY",
            "EXACT_CANONICAL_ARTIFACT_PREFIX_ONLY",
            "NO_FILENAME_TOKEN_SYMBOL_HEURISTICS",
            "ROLLOUT_SELECTION_REQUIRES_ACCEPTANCE_FILE",
            "TUPRS_EXCLUDED_AS_REFERENCE",
            "NO_NEW_SCORE",
            "NO_NEW_STORE",
            "NO_AL_SAT_SCANNER_RANKING_PORTFOLIO_MUTATION",
        ],
    }

    out = fi_dir / "FINANCIAL_INTELLIGENCE_V1_1_NEXT_REAL_SYMBOL_SELECTION.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"STATUS={status}")
    print(f"SCANNED_JSON_FILES={scanned_json}")
    print(f"CANDIDATE_COUNT={len(candidates)}")
    print(f"SELECTED_SYMBOL={payload['selected_symbol']}")
    print(f"SELECTED_ACCEPTANCE_FILE_COUNT={payload['selected_acceptance_file_count']}")
    for c in candidates[:10]:
        print(
            f"CANDIDATE={c['symbol']} "
            f"ACCEPTANCE={c['acceptance_file_count']} "
            f"CANONICAL={c['canonical_file_count']} "
            f"JSON_SYMBOL_FILES={c['json_symbol_file_count']}"
        )
    print(f"RESULT={out}")
    print("FINANCIAL_INTELLIGENCE_V1_1_NEXT_REAL_SYMBOL_SELECTOR_V2=PASS")

if __name__ == "__main__":
    main()
