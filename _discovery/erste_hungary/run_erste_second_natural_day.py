from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.funds.international.erste_hungary_bulk_metadata import fund_to_record
from backend.app.funds.international.erste_hungary_comparison import fetch_single_fund_comparison
from backend.app.funds.international.erste_hungary_rank_seed import build_rank_seed
from backend.app.funds.international.erste_hungary_rank_history import (
    load_history,
    seed_rank_history,
    two_date_fund_count,
)

def _jsonable(value):
    if isinstance(value, Decimal):
        return str(value)
    return value

def main() -> int:
    capture = ROOT / "_discovery" / "erste_hungary"
    base_path = capture / "bulk_metadata_v3_success.jsonl"
    history_path = capture / "rank_history_v1.json"

    today = date.today()
    day = today.isoformat()

    metadata_path = capture / f"bulk_metadata_daily_{day}.jsonl"
    failure_path = capture / f"bulk_metadata_daily_{day}_failures.jsonl"
    rank_path = capture / f"rank_seed_{day}.json"
    summary_path = capture / f"daily_refresh_{day}_summary.json"

    if metadata_path.exists() or rank_path.exists():
        print(f"DAILY_SNAPSHOT_ALREADY_EXISTS={day}")
        print("STATUS_FINAL=ALREADY_EXISTS_NO_MUTATION")
        return 0

    base_records = []
    with base_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                base_records.append(json.loads(line))

    isins = sorted({
        str(item["isin"]).strip().upper()
        for item in base_records
        if item.get("isin")
    })

    print(f"NATURAL_DATE={day}")
    print(f"TARGET_COUNT={len(isins)}")

    successes = []
    failures = []

    for index, isin in enumerate(isins, start=1):
        try:
            fund = fetch_single_fund_comparison(isin, timeout_seconds=40.0)
            successes.append(fund_to_record(fund))
            status = "SUCCESS"
        except Exception as exc:
            failures.append({
                "isin": isin,
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
            status = "FAIL"

        if index == 1 or index % 25 == 0 or index == len(isins) or status == "FAIL":
            print(
                f"PROGRESS={index}/{len(isins)}"
                f"|SUCCESS={len(successes)}"
                f"|FAIL={len(failures)}"
                f"|LAST={status}"
            )

    with metadata_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in successes:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    with failure_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in failures:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    print(f"SUCCESS_COUNT={len(successes)}")
    print(f"FAILURE_COUNT={len(failures)}")

    if failures:
        error_counts = Counter(item["error_type"] for item in failures)
        print("ERROR_TYPE_COUNTS=" + json.dumps(dict(error_counts), ensure_ascii=False))
        print("STATUS_FINAL=PARTIAL_SUCCESS_METADATA")
        return 2

    rows = build_rank_seed(successes)

    rank_payload = []
    for row in rows:
        rank_payload.append({
            key: _jsonable(value)
            for key, value in asdict(row).items()
        })

    rank_path.write_text(
        json.dumps(rank_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    ranked_count = sum(1 for row in rows if row.rank_position is not None)
    unmapped_count = sum(1 for row in rows if row.category_normalized is None)

    print(f"RANKED_COUNT={ranked_count}")
    print(f"UNMAPPED_CATEGORY_COUNT={unmapped_count}")

    history_result = seed_rank_history(
        rank_payload,
        rank_date=today,
        history_path=history_path,
    )

    history = load_history(history_path)
    date_counts = Counter(str(item["rank_date"]) for item in history)
    two_date_count = two_date_fund_count(history)

    summary = {
        "natural_date": day,
        "target_count": len(isins),
        "success_count": len(successes),
        "failure_count": len(failures),
        "ranked_count": ranked_count,
        "unmapped_category_count": unmapped_count,
        "history_inserted_count": history_result["inserted_count"],
        "history_skipped_existing_count": history_result["skipped_existing_count"],
        "history_row_count": history_result["history_row_count"],
        "unique_date_count": history_result["unique_date_count"],
        "unique_isin_count": history_result["unique_isin_count"],
        "two_date_fund_count": two_date_count,
        "rank_date_counts": dict(sorted(date_counts.items())),
    }

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"HISTORY_INSERTED_COUNT={history_result['inserted_count']}")
    print(f"HISTORY_SKIPPED_EXISTING_COUNT={history_result['skipped_existing_count']}")
    print(f"HISTORY_ROW_COUNT={history_result['history_row_count']}")
    print(f"UNIQUE_DATE_COUNT={history_result['unique_date_count']}")
    print(f"UNIQUE_ISIN_COUNT={history_result['unique_isin_count']}")
    print(f"TWO_DATE_FUND_COUNT={two_date_count}")
    print("RANK_DATE_COUNTS=" + json.dumps(dict(sorted(date_counts.items())), ensure_ascii=False))
    print(f"METADATA_JSONL=_discovery/erste_hungary/{metadata_path.name}")
    print(f"RANK_JSON=_discovery/erste_hungary/{rank_path.name}")
    print(f"SUMMARY_JSON=_discovery/erste_hungary/{summary_path.name}")
    print("PRODUCTION_STORE_MUTATION=NO")
    print("AL_SAT_MUTATION=NO")
    print("FORCED_FILL=NO")
    print("SYNTHETIC_DATE=NO")
    print("STATUS_FINAL=SUCCESS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())