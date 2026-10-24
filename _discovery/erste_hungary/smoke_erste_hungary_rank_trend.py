from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.funds.international.erste_hungary_rank_trend import (
    TREND_VERSION,
    evidence_from_movement_row,
)


def main() -> int:
    capture = ROOT / "_discovery" / "erste_hungary"
    movement_path = capture / "two_day_rank_movement_latest.json"
    output_path = capture / "rank_trend_evidence_v1_latest.json"
    summary_path = capture / "rank_trend_evidence_v1_summary_latest.json"

    movement = json.loads(movement_path.read_text(encoding="utf-8"))

    date_1 = str(movement["date_1"])
    date_2 = str(movement["date_2"])

    rows = []
    for bucket in ("top_improvers", "top_weakeners"):
        for row in movement.get(bucket, []):
            rows.append(
                evidence_from_movement_row(
                    row,
                    date_1=date_1,
                    date_2=date_2,
                )
            )

    # Build evidence for all funds directly from rank history comparison.
    history = json.loads(
        (capture / "rank_history_v1.json").read_text(encoding="utf-8")
    )

    by_date = {date_1: {}, date_2: {}}
    for item in history:
        d = str(item["rank_date"])
        if d in by_date:
            by_date[d][str(item["isin"]).upper()] = item

    all_evidence = []
    common = sorted(set(by_date[date_1]) & set(by_date[date_2]))

    for isin in common:
        old = by_date[date_1][isin]
        new = by_date[date_2][isin]

        all_evidence.append(
            evidence_from_movement_row(
                {
                    "isin": isin,
                    "category_normalized": new["category_normalized"],
                    "rank_1": old["rank_position"],
                    "rank_2": new["rank_position"],
                },
                date_1=date_1,
                date_2=date_2,
            )
        )

    payload = [asdict(item) for item in all_evidence]

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    direction_counts = Counter(item.direction for item in all_evidence)
    strength_counts = Counter(item.strength for item in all_evidence)

    category_direction_counts = {}
    categories = sorted({item.category_normalized for item in all_evidence})

    for category in categories:
        group = [item for item in all_evidence if item.category_normalized == category]
        category_direction_counts[category] = dict(
            Counter(item.direction for item in group)
        )

    strong_improving = [
        item for item in all_evidence
        if item.direction == "IMPROVING" and item.strength == "STRONG"
    ]
    strong_weakening = [
        item for item in all_evidence
        if item.direction == "WEAKENING" and item.strength == "STRONG"
    ]

    summary = {
        "trend_version": TREND_VERSION,
        "date_1": date_1,
        "date_2": date_2,
        "evidence_count": len(all_evidence),
        "direction_counts": dict(direction_counts),
        "strength_counts": dict(strength_counts),
        "category_direction_counts": category_direction_counts,
        "strong_improving_count": len(strong_improving),
        "strong_weakening_count": len(strong_weakening),
        "trade_authority": "NONE",
    }

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"TREND_VERSION={TREND_VERSION}")
    print(f"DATE_1={date_1}")
    print(f"DATE_2={date_2}")
    print(f"EVIDENCE_COUNT={len(all_evidence)}")
    print("DIRECTION_COUNTS=" + json.dumps(dict(direction_counts), ensure_ascii=False))
    print("STRENGTH_COUNTS=" + json.dumps(dict(strength_counts), ensure_ascii=False))
    print(f"STRONG_IMPROVING_COUNT={len(strong_improving)}")
    print(f"STRONG_WEAKENING_COUNT={len(strong_weakening)}")

    for item in sorted(
        strong_improving,
        key=lambda x: (-x.rank_delta, x.rank_2, x.isin),
    )[:10]:
        print(
            f"STRONG_IMPROVER={item.isin}"
            f"|category={item.category_normalized}"
            f"|rank={item.rank_1}->{item.rank_2}"
            f"|delta=+{item.rank_delta}"
        )

    for item in sorted(
        strong_weakening,
        key=lambda x: (x.rank_delta, -x.rank_2, x.isin),
    )[:10]:
        print(
            f"STRONG_WEAKENER={item.isin}"
            f"|category={item.category_normalized}"
            f"|rank={item.rank_1}->{item.rank_2}"
            f"|delta={item.rank_delta}"
        )

    print("OUTPUT_JSON=_discovery/erste_hungary/rank_trend_evidence_v1_latest.json")
    print("SUMMARY_JSON=_discovery/erste_hungary/rank_trend_evidence_v1_summary_latest.json")
    print("PRODUCTION_STORE_MUTATION=NO")
    print("AL_SAT_MUTATION=NO")
    print("FORCED_FILL=NO")
    print("TRADE_AUTHORITY=NONE")
    print("STATUS_FINAL=SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())