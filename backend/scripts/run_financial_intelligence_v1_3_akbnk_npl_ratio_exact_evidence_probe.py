from __future__ import annotations
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
data_dir = root / "backend" / "data" / "financial_intelligence"

# Prefer the existing normalized PDF text artifact; fall back to likely extracted text/json artifacts.
patterns = [
    "*AKBNK*KAP*PDF*TEXT*.txt",
    "*AKBNK*PDF*TEXT*.txt",
    "*AKBNK*PDF*EXTRACT*.txt",
    "*AKBNK*KAP*PDF*.txt",
    "*AKBNK*.txt",
    "*AKBNK*.json",
]

candidates = []
seen = set()
for pat in patterns:
    for p in data_dir.glob(pat):
        if p.is_file() and p not in seen:
            seen.add(p)
            candidates.append(p)

if not candidates:
    raise SystemExit(f"AKBNK_NORMALIZED_EVIDENCE_NOT_FOUND:{data_dir}")

# Narrow semantic anchors only; no broad source scan.
anchors = [
    "takipteki",
    "takipte bulunan",
    "donuk alacak",
    "donuk kred",
    "sorunlu kred",
    "non-performing",
    "non performing",
    "npl",
]

def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        return ""

raw_hits = []
for path in candidates:
    text = load_text(path)
    if not text:
        continue
    low = text.casefold()
    for anchor in anchors:
        a = anchor.casefold()
        pos = 0
        while True:
            idx = low.find(a, pos)
            if idx < 0:
                break
            start = max(0, idx - 650)
            end = min(len(text), idx + 950)
            context = " ".join(text[start:end].split())
            raw_hits.append((str(path), anchor, context))
            pos = idx + max(1, len(a))

# De-duplicate contexts.
dedup = []
seen_ctx = set()
for path, anchor, ctx in raw_hits:
    key = ctx
    if key in seen_ctx:
        continue
    seen_ctx.add(key)
    dedup.append((path, anchor, ctx))

pct_re = re.compile(r'(?<!\d)(?:%?\s*)\d{1,3}(?:[.,]\d+)?\s*%')
ratio_words = (
    "oran", "ratio", "toplam kredi", "kredilere oran", "nakdi kredi",
    "brüt kredi", "gross", "loan"
)

contexts = []
exact_candidates = []
for i, (path, anchor, ctx) in enumerate(dedup[:80], start=1):
    percentages = pct_re.findall(ctx)
    item = {
        "index": i,
        "source_path": path,
        "anchor": anchor,
        "percentages": percentages,
        "context": ctx,
    }
    contexts.append(item)
    clow = ctx.casefold()
    if percentages and any(w.casefold() in clow for w in ratio_words):
        exact_candidates.append(item)

# Fail closed: this probe reports candidate evidence only.
result = {
    "schema_version": "financial-intelligence-v1-3-akbnk-npl-ratio-exact-evidence-probe-v1",
    "status": "PASS",
    "target_metric": "ASSET_QUALITY.npl_ratio",
    "candidate_context_count": len(contexts),
    "exact_candidate_context_count": len(exact_candidates),
    "metric_value_selected": None,
    "selection_ready": False,
    "production_evidence": bool(contexts),
    "canonical_production_ready": False,
    "scoring_ready": False,
    "activation_ready": False,
    "missing_to_zero": False,
    "industrial_threshold_reuse": False,
    "production_mutation": "NO",
    "store_mutation": "NO",
    "al_sat_mutation": "NO",
    "scanner_mutation": "NO",
    "ranking_mutation": "NO",
    "portfolio_mutation": "NO",
    "blockers": [] if contexts else ["NPL_SEMANTIC_EVIDENCE_NOT_FOUND"],
    "candidate_contexts": contexts,
}

result_path = data_dir / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_NPL_RATIO_EXACT_EVIDENCE_PROBE.json"
result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

print("AKBNK_NPL_RATIO_EXACT_EVIDENCE_PROBE=START")
print("STATUS=PASS")
print("TARGET_METRIC=ASSET_QUALITY.npl_ratio")
print(f"CANDIDATE_CONTEXT_COUNT={len(contexts)}")
print(f"EXACT_CANDIDATE_CONTEXT_COUNT={len(exact_candidates)}")
print("METRIC_VALUE_SELECTED=None")
print("SELECTION_READY=False")
print(f"PRODUCTION_EVIDENCE={bool(contexts)}")
print("CANONICAL_PRODUCTION_READY=False")
print("SCORING_READY=False")
print("ACTIVATION_READY=False")
print("MISSING_TO_ZERO=False")
print("INDUSTRIAL_THRESHOLD_REUSE=False")
print(f"BLOCKERS={result['blockers']}")
print("CANDIDATE_CONTEXTS_START")
for item in contexts[:40]:
    print(f"--- CANDIDATE_{item['index']} ---")
    print(f"ANCHOR={item['anchor']}")
    print(f"PERCENTAGES={item['percentages']}")
    print(f"CONTEXT={item['context']}")
print("CANDIDATE_CONTEXTS_END")
print(f"RESULT={result_path}")
