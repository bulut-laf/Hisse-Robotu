import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path("_discovery/erste_hungary")
TARGET_DATE = "2026-10-07"
DELAY_SECONDS = 0.25

catalog = json.loads(
    (ROOT / "universe_catalog_v2_latest.json").read_text(encoding="utf-8")
)
old_catalog = json.loads(
    (ROOT / "universe_paginated_latest.json").read_text(encoding="utf-8")
)
old_isins = set(old_catalog["isins"])

sample = [
    (isin, url)
    for isin, url in zip(catalog["isins"], catalog["detail_urls"])
    if isin in old_isins
]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.erstemarket.hu/",
    "X-Requested-With": "XMLHttpRequest",
}

def fetch(url):
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=25) as response:
        return response.read().decode("utf-8", errors="replace")

results = []
total = len(sample)

for index, (isin, detail_url) in enumerate(sample, 1):
    row = {
        "isin": isin,
        "instrument_id": None,
        "nav_points": 0,
        "target_date_found": False,
        "nav_target_date": None,
        "latest_date": None,
        "error": None,
    }

    try:
        html = fetch(detail_url)
        ids = [
            value for value in re.findall(
                r'instrument-id=["\'](\d+)["\']', html
            )
            if value != "0"
        ]

        if not ids:
            raise ValueError("INSTRUMENT_ID_NOT_FOUND")

        row["instrument_id"] = ids[0]
        data = json.loads(
            fetch(f"https://www.erstemarket.hu/funds/chart/{ids[0]}")
        )
        series = data.get("series", [])
        row["nav_points"] = len(series)

        if not series:
            raise ValueError("EMPTY_NAV_SERIES")

        dated_points = []
        for timestamp_ms, nav in series:
            day = datetime.fromtimestamp(
                timestamp_ms / 1000, tz=timezone.utc
            ).date().isoformat()
            dated_points.append((day, nav))

        row["latest_date"] = max(day for day, _ in dated_points)

        target_values = [
            nav for day, nav in dated_points if day == TARGET_DATE
        ]
        if target_values:
            row["target_date_found"] = True
            row["nav_target_date"] = target_values[-1]

    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {str(exc)[:180]}"

    results.append(row)

    if index % 25 == 0 or index == total:
        successes = sum(r["target_date_found"] for r in results)
        errors = sum(r["error"] is not None for r in results)
        print(
            f"PROGRESS {index}/{total} | "
            f"TARGET_DATE_OK={successes} | ERRORS={errors}"
        )

    time.sleep(DELAY_SECONDS)

success_count = sum(r["target_date_found"] for r in results)
error_count = sum(r["error"] is not None for r in results)
missing_target = sum(
    r["error"] is None and not r["target_date_found"] for r in results
)

output = ROOT / "historical_nav_old929_20261007_coverage.json"
output.write_text(json.dumps({
    "artifact_type": "HISTORICAL_NAV_COVERAGE_DISCOVERY",
    "observation_date": TARGET_DATE,
    "requested_old_fund_count": len(old_isins),
    "processed_count": len(results),
    "target_date_success_count": success_count,
    "target_date_missing_count": missing_target,
    "error_count": error_count,
    "success_ratio": success_count / len(results) if results else 0,
    "results": results,
    "rank_history_write": False,
    "historical_backfill": False,
    "production_decisions_modified": False,
    "trade_authority": "NONE",
    "forced_fill": False,
}, ensure_ascii=False, indent=2), encoding="utf-8")

print("\nREPORT:", output)
print("PROCESSED:", len(results))
print("TARGET_DATE_SUCCESS:", success_count, "/", len(results))
print("TARGET_DATE_MISSING:", missing_target)
print("ERRORS:", error_count)
print("RANK_HISTORY_MODIFIED: False")
print("PRODUCTION_DECISIONS_MODIFIED: False")
print("TRADE_AUTHORITY: NONE")
print("FORCED_FILL: False")
