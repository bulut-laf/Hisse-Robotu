import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path("_discovery/erste_hungary")
TARGET_DATE = "2026-10-07"
SAMPLE_SIZE = 20

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
][:SAMPLE_SIZE]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.erstemarket.hu/",
    "X-Requested-With": "XMLHttpRequest",
}

def fetch(url):
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")

results = []

for index, (isin, detail_url) in enumerate(sample, 1):
    row = {
        "isin": isin,
        "instrument_id": None,
        "nav_points": 0,
        "target_date_found": False,
        "nav_target_date": None,
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
        data = json.loads(fetch(
            f"https://www.erstemarket.hu/funds/chart/{ids[0]}"
        ))
        series = data.get("series", [])
        row["nav_points"] = len(series)

        for timestamp_ms, nav in series:
            day = datetime.fromtimestamp(
                timestamp_ms / 1000, tz=timezone.utc
            ).date().isoformat()
            if day == TARGET_DATE:
                row["target_date_found"] = True
                row["nav_target_date"] = nav
                break

    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {str(exc)[:160]}"

    results.append(row)
    print(
        f"{index:02}/{len(sample)} {isin} "
        f"id={row['instrument_id']} points={row['nav_points']} "
        f"target={row['target_date_found']} error={row['error']}"
    )
    time.sleep(0.25)

output = ROOT / "historical_nav_old20_probe_20261007_v2.json"
success_count = sum(
    row["nav_points"] > 0 and row["target_date_found"]
    for row in results
)

output.write_text(json.dumps({
    "artifact_type": "HISTORICAL_NAV_ACCESS_PROBE",
    "observation_date": TARGET_DATE,
    "sample_size": len(results),
    "success_with_target_date": success_count,
    "results": results,
    "rank_history_write": False,
    "production_decisions_modified": False,
    "trade_authority": "NONE",
    "forced_fill": False,
}, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"\nREPORT: {output}")
print(f"TARGET_DATE_SUCCESS: {success_count}/{len(results)}")
print("RANK_HISTORY_MODIFIED: False")
print("PRODUCTION_DECISIONS_MODIFIED: False")
print("TRADE_AUTHORITY: NONE")
print("FORCED_FILL: False")
