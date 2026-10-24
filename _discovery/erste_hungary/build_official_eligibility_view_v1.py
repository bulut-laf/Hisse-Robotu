from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DISCOVERY = ROOT / "_discovery" / "erste_hungary"


def build_eligibility_view(
    seed: list[dict],
    official_review: dict,
) -> dict:
    records = official_review.get("records", [])
    excluded = {
        str(item["isin"]).strip().upper()
        for item in records
        if item.get("ranking_eligible") is False and item.get("isin")
    }

    present = {
        str(item.get("isin", "")).strip().upper()
        for item in seed
    }
    remaining = [
        item for item in seed
        if str(item.get("isin", "")).strip().upper() not in excluded
    ]

    return {
        "artifact_type": "ERSTE_HUNGARY_OFFICIAL_ELIGIBILITY_VIEW_V1",
        "classification_scope": "DISCOVERY_ONLY",
        "source_seed": "rank_seed_latest.json",
        "source_official_review": "official_fund_status_review_v1.json",
        "original_seed_count": len(seed),
        "excluded_count": len(excluded),
        "excluded_match_count": len(excluded & present),
        "eligible_view_count": len(remaining),
        "excluded_isins": sorted(excluded),
        "eligible_records": remaining,
        "rank_history_modified": False,
        "production_decisions_modified": False,
        "trade_authority": "NONE",
        "forced_fill": False,
    }


def main() -> int:
    seed_path = DISCOVERY / "rank_seed_latest.json"
    review_path = DISCOVERY / "official_fund_status_review_v1.json"
    output_path = DISCOVERY / "official_eligibility_view_v1.json"

    seed = json.loads(seed_path.read_text(encoding="utf-8-sig"))
    review = json.loads(review_path.read_text(encoding="utf-8-sig"))
    payload = build_eligibility_view(seed, review)

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("ORIGINAL_SEED_COUNT:", payload["original_seed_count"])
    print("EXCLUDED_COUNT:", payload["excluded_count"])
    print("EXCLUDED_MATCH_COUNT:", payload["excluded_match_count"])
    print("ELIGIBLE_VIEW_COUNT:", payload["eligible_view_count"])
    print("RANK_HISTORY_MODIFIED:", payload["rank_history_modified"])
    print("PRODUCTION_DECISIONS_MODIFIED:", payload["production_decisions_modified"])
    print("TRADE_AUTHORITY:", payload["trade_authority"])
    print("FORCED_FILL:", payload["forced_fill"])
    print("OUTPUT:", output_path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
