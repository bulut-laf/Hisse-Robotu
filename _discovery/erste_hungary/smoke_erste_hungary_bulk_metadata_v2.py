from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.funds.international.erste_hungary_bulk_metadata import (
    collect_bulk_metadata,
    load_completed_isins,
)


def main() -> int:
    capture_dir = ROOT / "_discovery" / "erste_hungary"
    universe_path = capture_dir / "universe_paginated_latest.json"

    success_path = capture_dir / "bulk_metadata_v2_success.jsonl"
    failure_path = capture_dir / "bulk_metadata_v2_failures.jsonl"
    summary_path = capture_dir / "bulk_metadata_v2_summary_latest.json"

    universe = json.loads(universe_path.read_text(encoding="utf-8"))
    isins = universe["isins"]

    def progress(index, total, success, fail, state):
        if (
            index == 1
            or index == total
            or index % 25 == 0
            or state == "FAIL"
        ):
            print(
                f"PROGRESS={index}/{total}"
                f"|SUCCESS={success}"
                f"|FAIL={fail}"
                f"|LAST={state}"
            )

    summary = collect_bulk_metadata(
        isins,
        success_jsonl=success_path,
        failure_jsonl=failure_path,
        timeout_seconds=40.0,
        request_delay_seconds=0.08,
        progress_callback=progress,
    )

    records = []
    if success_path.exists():
        with success_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

    fields = [
        "isin",
        "name",
        "fund_manager",
        "inception_date",
        "currency",
        "return_ytd",
        "return_1y",
        "return_5y",
        "volatility_1y",
        "volatility_3y",
        "volatility_5y",
        "max_drawdown_1y",
        "max_drawdown_5y",
        "nav",
        "nav_date",
        "net_asset_value",
        "category_raw",
        "risk_raw",
    ]

    field_coverage = {}
    for field in fields:
        non_null = sum(
            1
            for item in records
            if item.get(field) not in (None, "", "-")
        )
        field_coverage[field] = {
            "non_null": non_null,
            "total": len(records),
            "ratio": (non_null / len(records)) if records else 0.0,
        }

    error_counts = Counter()
    if failure_path.exists():
        with failure_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                error_counts[str(payload.get("error_type") or "UNKNOWN")] += 1

    payload = {
        "target_count": summary.target_count,
        "already_completed_count": summary.already_completed_count,
        "attempted_count": summary.attempted_count,
        "success_count_this_run": summary.success_count,
        "failure_count_this_run": summary.failure_count,
        "completed_total_count": summary.completed_total_count,
        "remaining_count": summary.target_count - summary.completed_total_count,
        "field_coverage": field_coverage,
        "error_type_counts": dict(sorted(error_counts.items())),
    }

    summary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"TARGET_COUNT={summary.target_count}")
    print(f"ALREADY_COMPLETED_COUNT={summary.already_completed_count}")
    print(f"ATTEMPTED_COUNT={summary.attempted_count}")
    print(f"SUCCESS_COUNT_THIS_RUN={summary.success_count}")
    print(f"FAILURE_COUNT_THIS_RUN={summary.failure_count}")
    print(f"COMPLETED_TOTAL_COUNT={summary.completed_total_count}")
    print(f"REMAINING_COUNT={summary.target_count - summary.completed_total_count}")
    print(
        "ERROR_TYPE_COUNTS="
        + json.dumps(dict(sorted(error_counts.items())), ensure_ascii=False)
    )

    for field in fields:
        item = field_coverage[field]
        print(
            f"FIELD={field}"
            f"|NON_NULL={item['non_null']}"
            f"|TOTAL={item['total']}"
            f"|RATIO={item['ratio']:.6f}"
        )

    if summary.completed_total_count == summary.target_count:
        print("BULK_COVERAGE=COMPLETE")
    elif summary.completed_total_count > 0:
        print("BULK_COVERAGE=PARTIAL_RESUMABLE")
    else:
        print("BULK_COVERAGE=EMPTY")

    print("SUCCESS_JSONL=_discovery/erste_hungary/bulk_metadata_v2_success.jsonl")
    print("FAILURE_JSONL=_discovery/erste_hungary/bulk_metadata_v2_failures.jsonl")
    print("SUMMARY_JSON=_discovery/erste_hungary/bulk_metadata_v2_summary_latest.json")
    print("PRODUCTION_STORE_MUTATION=NO")
    print("AL_SAT_MUTATION=NO")
    print("STATUS_FINAL=SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())