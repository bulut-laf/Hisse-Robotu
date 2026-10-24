from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.funds.international.erste_hungary_rank_seed import (
    CATEGORY_VERSION,
    RANK_SEED_VERSION,
    build_rank_seed,
    load_jsonl,
)


def _jsonable(value):
    if isinstance(value, Decimal):
        return str(value)
    return value


def main() -> int:
    capture_dir = ROOT / "_discovery" / "erste_hungary"
    bulk_path = capture_dir / "bulk_metadata_success.jsonl"
    output_path = capture_dir / "rank_seed_latest.json"
    summary_path = capture_dir / "rank_seed_summary_latest.json"

    records = load_jsonl(bulk_path)
    rows = build_rank_seed(records)

    category_counts = Counter(
        row.category_normalized or "UNMAPPED"
        for row in rows
    )
    ranked_count = sum(1 for row in rows if row.rank_position is not None)
    unrated_count = len(rows) - ranked_count
    mapped_count = sum(
        1 for row in rows
        if row.category_normalized is not None
    )

    payload = []
    for row in rows:
        item = {
            key: _jsonable(value)
            for key, value in asdict(row).items()
        }
        payload.append(item)

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "category_version": CATEGORY_VERSION,
        "rank_seed_version": RANK_SEED_VERSION,
        "record_count": len(rows),
        "mapped_category_count": mapped_count,
        "unmapped_category_count": len(rows) - mapped_count,
        "ranked_count": ranked_count,
        "unranked_count": unrated_count,
        "category_counts": dict(sorted(category_counts.items())),
    }

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"RECORD_COUNT={len(rows)}")
    print(f"MAPPED_CATEGORY_COUNT={mapped_count}")
    print(f"UNMAPPED_CATEGORY_COUNT={len(rows) - mapped_count}")
    print(f"RANKED_COUNT={ranked_count}")
    print(f"UNRANKED_COUNT={unrated_count}")
    print(
        "CATEGORY_COUNTS="
        + json.dumps(dict(sorted(category_counts.items())), ensure_ascii=False)
    )

    for row in rows:
        if row.rank_position == 1:
            print(
                "CATEGORY_LEADER="
                + str(row.category_normalized)
                + "|isin=" + row.isin
                + "|score=" + str(row.rank_score)
                + "|size=" + str(row.category_size)
            )

    print("OUTPUT_JSON=_discovery/erste_hungary/rank_seed_latest.json")
    print("SUMMARY_JSON=_discovery/erste_hungary/rank_seed_summary_latest.json")
    print("PRODUCTION_STORE_MUTATION=NO")
    print("AL_SAT_MUTATION=NO")
    print("FORCED_FILL=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())