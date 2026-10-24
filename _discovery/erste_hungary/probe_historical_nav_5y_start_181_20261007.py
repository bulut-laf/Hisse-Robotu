import json
import time
import urllib.request
from datetime import datetime, date, timezone
from pathlib import Path
from collections import Counter

ROOT = Path("_discovery/erste_hungary")
INPUT = ROOT / "historical_nav_5y_coverage_classification_20261007.json"
OUTPUT = ROOT / "historical_nav_5y_start_probe_181_20261007.json"

CUTOFF = date(2021, 10, 7)
TARGET = date(2026, 10, 7)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.erstemarket.hu/",
    "X-Requested-With": "XMLHttpRequest",
}

def fetch_points(instrument_id):
    url = f"https://www.erstemarket.hu/funds/chart/{instrument_id}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))

    points = {}
    for item in payload.get("series", []):
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        try:
            day = datetime.fromtimestamp(
                float(item[0]) / 1000, tz=timezone.utc
            ).date()
            nav = float(item[1])
            if nav > 0:
                points[day] = nav
        except (ValueError, TypeError, OverflowError, OSError):
            continue

    return sorted(points.items())

def main():
    source = json.loads(INPUT.read_text(encoding="utf-8"))
    funds = source["classification"]["start_date_absent"]
    results = []

    for i, fund in enumerate(funds, 1):
        row = {
            "isin": fund["isin"],
            "instrument_id": fund["instrument_id"],
            "cutoff_date": CUTOFF.isoformat(),
            "target_date": TARGET.isoformat(),
            "point_count": 0,
            "earliest_nav_date": None,
            "latest_nav_date_on_or_before_target": None,
            "nav_on_or_before_cutoff_date": None,
            "nav_after_cutoff_first_date": None,
            "status": "PENDING",
            "classification": None,
            "error": None,
        }

        try:
            points = fetch_points(fund["instrument_id"])
            row["point_count"] = len(points)

            if not points:
                row["status"] = "EMPTY_SERIES"
                row["classification"] = "NO_HISTORICAL_NAV_SERIES"
            else:
                row["earliest_nav_date"] = points[0][0].isoformat()

                eligible = [(d, v) for d, v in points if d <= TARGET]
                if eligible:
                    row["latest_nav_date_on_or_before_target"] = (
                        eligible[-1][0].isoformat()
                    )

                before = [(d, v) for d, v in points if d <= CUTOFF]
                after = [(d, v) for d, v in points if d > CUTOFF]

                if before:
                    d, v = before[-1]
                    row["nav_on_or_before_cutoff_date"] = {
                        "date": d.isoformat(),
                        "nav": v,
                        "lag_days": (CUTOFF - d).days,
                    }
                    row["status"] = "CUTOFF_NAV_FOUND"
                    row["classification"] = "HISTORICAL_START_POINT_AVAILABLE"
                else:
                    row["status"] = "NO_NAV_ON_OR_BEFORE_CUTOFF"
                    if points[0][0] > CUTOFF:
                        row["classification"] = "SERIES_BEGINS_AFTER_5Y_CUTOFF"
                    else:
                        row["classification"] = "CUTOFF_POINT_NOT_FOUND_CHECK_SERIES"

                if after:
                    d, v = after[0]
                    row["nav_after_cutoff_first_date"] = {
                        "date": d.isoformat(),
                        "nav": v,
                    }

        except Exception as exc:
            row["status"] = "FETCH_ERROR"
            row["classification"] = "UNRESOLVED_FETCH_OR_PARSE"
            row["error"] = f"{type(exc).__name__}: {exc}"

        results.append(row)

        if i % 20 == 0 or i == len(funds):
            print(f"PROGRESS: {i}/{len(funds)}")
        time.sleep(0.25)

    counts = Counter(r["classification"] for r in results)
    output = {
        "artifact": "historical_nav_5y_start_probe_181_20261007",
        "reference_date": TARGET.isoformat(),
        "cutoff_date": CUTOFF.isoformat(),
        "input_count": len(funds),
        "result_count": len(results),
        "classification_counts": dict(counts),
        "definition": (
            "Checks whether the historical NAV series contains a point "
            "on or before 2021-10-07. Does not calculate or write ranks."
        ),
        "rank_history_write": False,
        "production_decisions_modified": False,
        "trade_authority": "NONE",
        "forced_fill": False,
        "results": results,
    }

    OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("CLASSIFICATIONS:", json.dumps(dict(counts), ensure_ascii=False))
    print("OUTPUT:", OUTPUT)
    print("RANK_HISTORY_MODIFIED: False")
    print("PRODUCTION_DECISIONS_MODIFIED: False")
    print("TRADE_AUTHORITY: NONE")
    print("FORCED_FILL: False")

if __name__ == "__main__":
    main()
