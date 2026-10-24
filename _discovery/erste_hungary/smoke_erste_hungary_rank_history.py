from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.funds.international.erste_hungary_rank_history import (
    RANK_HISTORY_VERSION,
    load_history,
    seed_rank_history,
    two_date_fund_count,
)


def main() -> int:
    capture_dir = ROOT / "_discovery" / "erste_hungary"
    seed_path = capture_dir / "rank_seed_v3_latest.json"
    history_path = capture_dir / "rank_history_v1.json"
    summary_path = capture_dir / "rank_history_v1_summary_latest.json"

    seed_rows = json.loads(seed_path.read_text(encoding="utf-8"))

    nav_dates = {
        str(item.get("nav_date"))
        for item in seed_rows
        if item.get("nav_date")
    }

    today = date.today()

    result = seed_rank_history(
        seed_rows,
        rank_date=today,
        history_path=history_path,
    )

    history = load_history(history_path)
    date_counts = Counter(
        str(item["rank_date"])
        for item in history
    )

    two_date_count = two_date_fund_count(history)

    summary = {
        "rank_history_version": RANK_HISTORY_VERSION,
        "rank_date": today.isoformat(),
        "inserted_count": result["inserted_count"],
        "skipped_existing_count": result["skipped_existing_count"],
        "history_row_count": result["history_row_count"],
        "unique_date_count": result["unique_date_count"],
        "unique_isin_count": result["unique_isin_count"],
        "two_date_fund_count": two_date_count,
        "rank_date_counts": dict(sorted(date_counts.items())),
    }

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"RANK_HISTORY_VERSION={RANK_HISTORY_VERSION}")
    print(f"NATURAL_RANK_DATE={today.isoformat()}")
    print(f"INSERTED_COUNT={result['inserted_count']}")
    print(f"SKIPPED_EXISTING_COUNT={result['skipped_existing_count']}")
    print(f"HISTORY_ROW_COUNT={result['history_row_count']}")
    print(f"UNIQUE_DATE_COUNT={result['unique_date_count']}")
    print(f"UNIQUE_ISIN_COUNT={result['unique_isin_count']}")
    print(f"TWO_DATE_FUND_COUNT={two_date_count}")
    print(
        "RANK_DATE_COUNTS="
        + json.dumps(dict(sorted(date_counts.items())), ensure_ascii=False)
    )

    print("HISTORY_JSON=_discovery/erste_hungary/rank_history_v1.json")
    print("SUMMARY_JSON=_discovery/erste_hungary/rank_history_v1_summary_latest.json")
    print("PRODUCTION_STORE_MUTATION=NO")
    print("AL_SAT_MUTATION=NO")
    print("FORCED_FILL=NO")
    print("SYNTHETIC_DATE=NO")
    print("STATUS_FINAL=SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())