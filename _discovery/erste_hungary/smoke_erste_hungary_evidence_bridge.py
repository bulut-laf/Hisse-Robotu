from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.funds.international.erste_hungary_evidence_bridge import (
    BRIDGE_VERSION,
    bridge_from_history_pair,
)


def main() -> int:
    capture = ROOT / "_discovery" / "erste_hungary"
    history_path = capture / "rank_history_v1.json"
    output_path = capture / "f1_evidence_bridge_v1_latest.json"
    summary_path = capture / "f1_evidence_bridge_v1_summary_latest.json"

    history = json.loads(history_path.read_text(encoding="utf-8"))
    dates = sorted({str(item["rank_date"]) for item in history})

    if len(dates) < 2:
        raise SystemExit("NEED_TWO_NATURAL_DATES")

    date_1, date_2 = dates[-2], dates[-1]

    by_date = {date_1: {}, date_2: {}}
    for item in history:
        d = str(item["rank_date"])
        if d in by_date:
            by_date[d][str(item["isin"]).upper()] = item

    common = sorted(set(by_date[date_1]) & set(by_date[date_2]))

    rows = []
    f1_state_counts = Counter()
    positive_change = 0
    negative_change = 0
    zero_change = 0

    for isin in common:
        result = bridge_from_history_pair(
            by_date[date_1][isin],
            by_date[date_2][isin],
        )

        value = result.evidence_input
        change = int(value.category_rank_change or 0)

        if change > 0:
            positive_change += 1
        elif change < 0:
            negative_change += 1
        else:
            zero_change += 1

        f1_state_counts[result.mapped_f1_state] += 1

        rows.append({
            "canonical_fund_id": value.canonical_fund_id,
            "isin": isin,
            "category_id": value.category_id,
            "category_rank_percentile": str(value.category_rank_percentile),
            "category_rank_change": value.category_rank_change,
            "f1_state": result.mapped_f1_state,
            "f1_facts": list(result.mapped_f1_facts),
            "f1_missing_fields": list(result.mapped_f1_missing_fields),
            "trade_authority": "NONE",
        })

    output_path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "bridge_version": BRIDGE_VERSION,
        "date_1": date_1,
        "date_2": date_2,
        "evidence_count": len(rows),
        "positive_rank_change_count": positive_change,
        "negative_rank_change_count": negative_change,
        "zero_rank_change_count": zero_change,
        "f1_state_counts": dict(f1_state_counts),
        "trade_authority": "NONE",
        "f1_store_mutation": False,
    }

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"BRIDGE_VERSION={BRIDGE_VERSION}")
    print(f"DATE_1={date_1}")
    print(f"DATE_2={date_2}")
    print(f"EVIDENCE_COUNT={len(rows)}")
    print(f"POSITIVE_RANK_CHANGE_COUNT={positive_change}")
    print(f"NEGATIVE_RANK_CHANGE_COUNT={negative_change}")
    print(f"ZERO_RANK_CHANGE_COUNT={zero_change}")
    print("F1_STATE_COUNTS=" + json.dumps(dict(f1_state_counts), ensure_ascii=False))

    for row in sorted(
        rows,
        key=lambda x: (-int(x["category_rank_change"]), x["isin"]),
    )[:10]:
        print(
            f"F1_SAMPLE={row['isin']}"
            f"|category={row['category_id']}"
            f"|percentile={row['category_rank_percentile']}"
            f"|rank_change={row['category_rank_change']}"
            f"|state={row['f1_state']}"
        )

    print("OUTPUT_JSON=_discovery/erste_hungary/f1_evidence_bridge_v1_latest.json")
    print("SUMMARY_JSON=_discovery/erste_hungary/f1_evidence_bridge_v1_summary_latest.json")
    print("TEFAS_MUTATION=NO")
    print("F1_STORE_MUTATION=NO")
    print("PRODUCTION_STORE_MUTATION=NO")
    print("AL_SAT_MUTATION=NO")
    print("FORCED_FILL=NO")
    print("TRADE_AUTHORITY=NONE")
    print("STATUS_FINAL=SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())