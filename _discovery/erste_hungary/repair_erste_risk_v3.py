from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.funds.international.erste_hungary_bulk_metadata import (
    fund_to_record,
)
from backend.app.funds.international.erste_hungary_comparison import (
    fetch_single_fund_comparison,
)

capture = ROOT / "_discovery" / "erste_hungary"
v2 = capture / "bulk_metadata_v2_success.jsonl"
v3 = capture / "bulk_metadata_v3_success.jsonl"
summary_path = capture / "bulk_metadata_v3_summary_latest.json"

records = []
with v2.open("r", encoding="utf-8") as handle:
    for line in handle:
        line = line.strip()
        if line:
            records.append(json.loads(line))

allowed_risks = {"Magas", "K\u00f6zepes", "Alacsony"}

anomalies = [
    record
    for record in records
    if record.get("risk_raw") not in allowed_risks
]

print(f"INPUT_COUNT={len(records)}")
print(f"RISK_ANOMALY_COUNT={len(anomalies)}")

replacement_by_isin = {}

for record in anomalies:
    isin = str(record["isin"]).strip().upper()
    print(f"REFETCH_ISIN={isin}")
    fund = fetch_single_fund_comparison(isin, timeout_seconds=40.0)
    replacement = fund_to_record(fund)
    replacement_by_isin[isin] = replacement
    print(
        "REFETCH_RESULT="
        + isin
        + "|risk_raw=" + str(replacement.get("risk_raw"))
        + "|category_raw=" + str(replacement.get("category_raw"))
        + "|name=" + str(replacement.get("name"))
    )

output_records = []
for record in records:
    isin = str(record["isin"]).strip().upper()
    output_records.append(replacement_by_isin.get(isin, record))

with v3.open("w", encoding="utf-8", newline="\n") as handle:
    for record in output_records:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

risk_counts = Counter(
    str(item.get("risk_raw"))
    for item in output_records
    if item.get("risk_raw") not in (None, "", "-")
)

missing_risk_count = sum(
    1 for item in output_records
    if item.get("risk_raw") in (None, "", "-")
)

invalid_risk_count = sum(
    1 for item in output_records
    if item.get("risk_raw") not in (None, "", "-")
    and item.get("risk_raw") not in allowed_risks
)

category_counts = Counter(
    str(item.get("category_raw"))
    for item in output_records
    if item.get("category_raw") not in (None, "", "-")
)

summary = {
    "record_count": len(output_records),
    "refetched_count": len(replacement_by_isin),
    "risk_counts": dict(risk_counts.most_common()),
    "missing_risk_count": missing_risk_count,
    "invalid_risk_count": invalid_risk_count,
    "category_counts": dict(category_counts.most_common()),
}

summary_path.write_text(
    json.dumps(summary, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"OUTPUT_COUNT={len(output_records)}")
print(f"REFETCHED_COUNT={len(replacement_by_isin)}")
print(f"MISSING_RISK_COUNT={missing_risk_count}")
print(f"INVALID_RISK_COUNT={invalid_risk_count}")
print("RISK_COUNTS=" + json.dumps(dict(risk_counts.most_common()), ensure_ascii=False))
print("CATEGORY_COUNTS=" + json.dumps(dict(category_counts.most_common()), ensure_ascii=False))
print("OUTPUT_JSONL=_discovery/erste_hungary/bulk_metadata_v3_success.jsonl")
print("SUMMARY_JSON=_discovery/erste_hungary/bulk_metadata_v3_summary_latest.json")
print("PRODUCTION_STORE_MUTATION=NO")
print("STATUS_FINAL=SUCCESS")