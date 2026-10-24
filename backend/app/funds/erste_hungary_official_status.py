from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACT = (
    PROJECT_ROOT
    / "_discovery"
    / "erste_hungary"
    / "official_fund_status_review_v1.json"
)


def load_erste_hungary_official_status(
    artifact_path: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    path = Path(artifact_path) if artifact_path is not None else DEFAULT_ARTIFACT

    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise ValueError("OFFICIAL_STATUS_RECORDS_MISSING")

    result: dict[str, dict[str, Any]] = {}

    for item in payload["records"]:
        if not isinstance(item, dict):
            raise ValueError("OFFICIAL_STATUS_ROW_NOT_OBJECT")

        isin = str(item.get("isin", "")).strip().upper()
        if not isin:
            raise ValueError("OFFICIAL_STATUS_ISIN_MISSING")
        if isin in result:
            raise ValueError("DUPLICATE_OFFICIAL_STATUS_ISIN:" + isin)

        eligible = item.get("ranking_eligible")
        if not isinstance(eligible, bool):
            raise ValueError("INVALID_RANKING_ELIGIBILITY:" + isin)

        result[isin] = {
            "status": str(item.get("status", "UNKNOWN")),
            "ranking_eligible": eligible,
            "last_nav_date": item.get(
                "last_official_nav_date",
                item.get("last_nav_date"),
            ),
            "liquidation_effective_date": item.get("liquidation_effective_date"),
            "source": str(item.get("source", "")).strip(),
        }

    if payload.get("trade_authority") != "NONE":
        raise ValueError("TRADE_AUTHORITY_NOT_NONE")
    if payload.get("forced_fill") is not False:
        raise ValueError("FORCED_FILL_TRUE")

    return result
