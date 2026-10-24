from collections import Counter
from decimal import Decimal
from pathlib import Path
import dataclasses
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.app.funds.evidence_mapper import map_fund_evidence
from backend.app.funds.analysis_engine import analyze_fund
from backend.app.funds.international.erste_hungary_f3_bridge import (
    F3_BRIDGE_VERSION,
    build_f1_f3_input,
    category_volatility_percentiles,
)

capture = ROOT / "_discovery" / "erste_hungary"
meta_path = capture / "bulk_metadata_daily_2026-09-25.jsonl"
f1_path = capture / "f1_evidence_bridge_v1_latest.json"
output_path = capture / "f1_f3_evidence_v1_latest.json"
summary_path = capture / "f1_f3_evidence_v1_summary_latest.json"

meta_rows = [
    json.loads(line)
    for line in meta_path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
f1_rows = json.loads(f1_path.read_text(encoding="utf-8"))

category_map = {
    "R\u00e9szv\u00e9ny": "EQUITY",
    "K\u00f6tv\u00e9ny": "BOND",
    "Abszol\u00fat hozam\u00fa": "ABSOLUTE_RETURN",
    "Vegyes": "MIXED",
    "P\u00e9nzpiac": "MONEY_MARKET",
    "Nyersanyag": "COMMODITY",
    "Ingatlan": "REAL_ESTATE",
    "Alapok alapja": "FUND_OF_FUNDS",
    "Sz\u00e1rmaztatott": "DERIVATIVE",
}

for row in meta_rows:
    row["category_normalized"] = category_map.get(row.get("category_raw"))

vol_pct = category_volatility_percentiles(meta_rows)
meta_by_isin = {str(r["isin"]).upper(): r for r in meta_rows}

f3_counts = Counter()
class_counts = Counter()
eligibility_counts = Counter()
trade_counts = Counter()
rows = []

for f1 in f1_rows:
    isin = str(f1["isin"]).upper()
    meta = meta_by_isin[isin]

    vol = vol_pct.get(isin)
    dd_raw = meta.get("max_drawdown_1y")
    dd = None if dd_raw in (None, "", "-") else Decimal(str(dd_raw))

    value = build_f1_f3_input(
        isin=isin,
        category_normalized=f1["category_id"],
        category_rank_percentile=Decimal(str(f1["category_rank_percentile"])),
        category_rank_change=int(f1["category_rank_change"]),
        volatility_percentile=vol,
        max_drawdown_1y=dd,
    )

    mapped = map_fund_evidence(value)
    f3 = next(item for item in mapped.evidence if item.family == "F3")
    result = analyze_fund(mapped)

    f3_counts[str(f3.state)] += 1
    class_counts[result.classification] += 1
    eligibility_counts[result.eligibility_reason] += 1
    trade_counts[result.automatic_trade_authority] += 1

    rows.append({
        "isin": isin,
        "canonical_fund_id": result.canonical_fund_id,
        "category_id": result.category_id,
        "f1_state": f1["f1_state"],
        "f3_state": str(f3.state),
        "volatility_percentile": None if vol is None else str(vol),
        "max_drawdown_1y": None if dd is None else str(dd),
        "classification": result.classification,
        "eligibility_reason": result.eligibility_reason,
        "automatic_trade_authority": result.automatic_trade_authority,
        "forced_fill": result.forced_fill,
    })

output_path.write_text(
    json.dumps(rows, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

summary = {
    "version": F3_BRIDGE_VERSION,
    "result_count": len(rows),
    "f3_state_counts": dict(f3_counts),
    "class_counts": dict(class_counts),
    "eligibility_counts": dict(eligibility_counts),
    "trade_authority_counts": dict(trade_counts),
}
summary_path.write_text(
    json.dumps(summary, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"F3_BRIDGE_VERSION={F3_BRIDGE_VERSION}")
print(f"RESULT_COUNT={len(rows)}")
print("F3_STATE_COUNTS=" + json.dumps(dict(f3_counts), ensure_ascii=False))
print("CLASS_COUNTS=" + json.dumps(dict(class_counts), ensure_ascii=False))
print("ELIGIBILITY_COUNTS=" + json.dumps(dict(eligibility_counts), ensure_ascii=False))
print("TRADE_AUTHORITY_COUNTS=" + json.dumps(dict(trade_counts), ensure_ascii=False))

for row in [r for r in rows if r["classification"] != "X"][:20]:
    print(
        "NON_X="
        + row["isin"]
        + "|class=" + row["classification"]
        + "|f1=" + row["f1_state"]
        + "|f3=" + row["f3_state"]
        + "|eligibility=" + row["eligibility_reason"]
        + "|trade=" + row["automatic_trade_authority"]
    )

print("OUTPUT_JSON=_discovery/erste_hungary/f1_f3_evidence_v1_latest.json")
print("SUMMARY_JSON=_discovery/erste_hungary/f1_f3_evidence_v1_summary_latest.json")
print("TEFAS_MUTATION=NO")
print("F1_STORE_MUTATION=NO")
print("PRODUCTION_STORE_MUTATION=NO")
print("AL_SAT_MUTATION=NO")
print("FORCED_FILL=NO")
print("TRADE_AUTHORITY=NONE")
print("STATUS_FINAL=SUCCESS")