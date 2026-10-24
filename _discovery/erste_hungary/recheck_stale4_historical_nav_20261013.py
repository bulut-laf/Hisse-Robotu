import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path("_discovery/erste_hungary")
SOURCE = ROOT / "historical_nav_old929_20261007_coverage.json"
OUTPUT = ROOT / "historical_nav_stale4_recheck_20261013.json"

TARGET_ISINS = {
    "LU0011850392",
    "LU0113311731",
    "LU0117895796",
    "LU0823403356",
}

report = json.loads(SOURCE.read_text(encoding="utf-8"))
source_rows = {
    row["isin"]: row
    for row in report["results"]
    if row.get("isin") in TARGET_ISINS
}

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.erstemarket.hu/",
    "X-Requested-With": "XMLHttpRequest",
}

results = []

for isin in sorted(TARGET_ISINS):
    original = source_rows.get(isin, {})
    row = {
        "isin": isin,
        "instrument_id": original.get("instrument_id"),
        "previous_latest_date": original.get("latest_date"),
        "http_status": None,
        "nav_points": 0,
        "latest_date": None,
        "latest_nav": None,
        "target_date_found": False,
        "nav_2026_10_07": None,
        "nav_2026_10_08": None,
        "nav_2026_10_09": None,
        "error": None,
    }

    try:
        instrument_id = row["instrument_id"]
        if not instrument_id:
            raise ValueError("MISSING_INSTRUMENT_ID")

        req = Request(
            f"https://www.erstemarket.hu/funds/chart/{instrument_id}",
            headers=headers,
        )
        with urlopen(req, timeout=25) as response:
            row["http_status"] = response.status
            data = json.loads(
                response.read().decode("utf-8", errors="replace")
            )

        dated = {}
        for timestamp_ms, nav in data.get("series", []):
            day = datetime.fromtimestamp(
                timestamp_ms / 1000, tz=timezone.utc
            ).date().isoformat()
            dated[day] = nav

        row["nav_points"] = len(data.get("series", []))
        row["latest_date"] = max(dated) if dated else None
        if row["latest_date"]:
            row["latest_nav"] = dated[row["latest_date"]]

        for day in ("2026-10-07", "2026-10-08", "2026-10-09"):
            row[f"nav_{day.replace('-', '_')}"] = dated.get(day)

        row["target_date_found"] = "2026-10-07" in dated

    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

    results.append(row)
    print(
        f"{isin} | id={row['instrument_id']} "
        f"| points={row['nav_points']} "
        f"| latest={row['latest_date']} "
        f"| error={row['error']}"
    )

output_data = {
    "artifact_type": "HISTORICAL_NAV_STALE4_RECHECK",
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "source_report": str(SOURCE),
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
print(f"\nOUTPUT: {OUTPUT}")
print("RANK_HISTORY_WRITE: False")
print("PRODUCTION_DECISIONS_MODIFIED: False")
print("TRADE_AUTHORITY: NONE")
print("FORCED_FILL: False")
