import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path("_discovery/erste_hungary")
SOURCE = ROOT / "historical_nav_old929_20261007_coverage.json"
OUTPUT = ROOT / "historical_nav_missing34_diagnostic_20261007.json"

report = json.loads(SOURCE.read_text(encoding="utf-8"))
missing = [
    row for row in report["results"]
    if not row["target_date_found"] or row["error"]
]

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.erstemarket.hu/",
    "X-Requested-With": "XMLHttpRequest",
}

def fetch(url):
    req = Request(url, headers=headers)
    with urlopen(req, timeout=25) as response:
        return response.status, response.read().decode("utf-8", errors="replace")

results = []

for i, original in enumerate(missing, 1):
    row = {
        "isin": original["isin"],
        "instrument_id": original.get("instrument_id"),
        "previous_error": original.get("error"),
        "retry_error": None,
        "retry_http_status": None,
        "retry_nav_points": 0,
        "retry_latest_date": None,
        "target_date_found": False,
        "nav_2026_10_07": None,
        "nav_2026_10_08": None,
        "nav_2026_10_09": None,
    }

    try:
        instrument_id = row["instrument_id"]
        if not instrument_id:
            raise ValueError("MISSING_INSTRUMENT_ID")

        status, body = fetch(
            f"https://www.erstemarket.hu/funds/chart/{instrument_id}"
        )
        row["retry_http_status"] = status
        data = json.loads(body)
        series = data.get("series", [])
        row["retry_nav_points"] = len(series)

        dated = {}
        invalid_timestamps = 0
        for timestamp_ms, nav in series:
            try:
                day = (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=float(timestamp_ms))).date().isoformat()
                dated[day] = nav
            except (ValueError, TypeError, OverflowError):
                invalid_timestamps += 1
        row['invalid_timestamps'] = invalid_timestamps

        row["retry_latest_date"] = max(dated) if dated else None
        for day in ("2026-10-07", "2026-10-08", "2026-10-09"):
            value = dated.get(day)
            row[f"nav_{day.replace('-', '_')}"] = value

        row["target_date_found"] = "2026-10-07" in dated

    except Exception as exc:
        row["retry_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

    results.append(row)
    print(
        f"{i:02}/{len(missing)} {row['isin']} "
        f"id={row['instrument_id']} points={row['retry_nav_points']} "
        f"target={row['target_date_found']} "
        f"latest={row['retry_latest_date']} "
        f"error={row['retry_error']}"
    )
    time.sleep(0.35)

output_data = {
    "artifact_type": "HISTORICAL_NAV_MISSING_DATE_DIAGNOSTIC",
    "target_date": "2026-10-07",
    "source_report": str(SOURCE),
    "diagnosed_count": len(results),
    "target_date_success_count": sum(r["target_date_found"] for r in results),
    "retry_error_count": sum(r["retry_error"] is not None for r in results),
    "results": results,
    "rank_history_write": False,
    "production_decisions_modified": False,
    "trade_authority": "NONE",
    "forced_fill": False,
}

OUTPUT.write_text(
    json.dumps(output_data, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("\nREPORT:", OUTPUT)
print("DIAGNOSED:", len(results))
print("TARGET_DATE_NOW_FOUND:", output_data["target_date_success_count"])
print("RETRY_ERRORS:", output_data["retry_error_count"])
print("RANK_HISTORY_MODIFIED: False")
print("PRODUCTION_DECISIONS_MODIFIED: False")
print("TRADE_AUTHORITY: NONE")
print("FORCED_FILL: False")

