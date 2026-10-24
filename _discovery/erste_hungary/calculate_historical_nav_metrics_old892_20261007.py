import json
import time
import math
import urllib.request
import urllib.error
from datetime import datetime, date, timezone
from pathlib import Path

ROOT = Path("_discovery/erste_hungary")
COVERAGE_PATH = ROOT / "historical_nav_old929_20261007_coverage.json"
OUTPUT_PATH = ROOT / "historical_nav_metrics_old892_20261007.json"

TARGET = date(2026, 10, 7)
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.erstemarket.hu/",
    "X-Requested-With": "XMLHttpRequest",
}

def parse_points(payload):
    raw = payload.get("series", [])
    points = []
    for item in raw:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        try:
            day = datetime.fromtimestamp(
                float(item[0]) / 1000, tz=timezone.utc
            ).date()
            nav = float(item[1])
            if math.isfinite(nav) and nav > 0:
                points.append((day, nav))
        except (TypeError, ValueError, OverflowError, OSError):
            continue

    # Same-date duplicates: retain the last point in source order.
    by_date = {}
    for day, nav in points:
        by_date[day] = nav
    return sorted(by_date.items())

def fetch_series(instrument_id):
    url = f"https://www.erstemarket.hu/funds/chart/{instrument_id}"
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
    payload = json.loads(body)
    return parse_points(payload)

def point_at_or_before(points, cutoff):
    candidates = [(d, v) for d, v in points if d <= cutoff]
    return candidates[-1] if candidates else None

def relative_return(points, target_day, start_day, max_lag_days=7):
    start = point_at_or_before(points, start_day)
    end = point_at_or_before(points, target_day)
    if start is None or end is None:
        return None, None
    if (start_day - start[0]).days > max_lag_days:
        return None, start[0].isoformat()
    if start[1] <= 0:
        return None, start[0].isoformat()
    return end[1] / start[1] - 1.0, start[0].isoformat()

def cagr_5y(points, target_day):
    start = point_at_or_before(points, date(2021, 10, 7))
    end = point_at_or_before(points, target_day)
    if start is None or end is None:
        return None, None
    lag = (date(2021, 10, 7) - start[0]).days
    if lag > 7 or start[1] <= 0:
        return None, start[0].isoformat()
    elapsed_days = (end[0] - start[0]).days
    if elapsed_days <= 0:
        return None, start[0].isoformat()
    return (end[1] / start[1]) ** (365.2425 / elapsed_days) - 1.0, start[0].isoformat()

def max_drawdown_1y(points, target_day):
    start_cutoff = date(2025, 10, 7)
    start = point_at_or_before(points, start_cutoff)
    end = point_at_or_before(points, target_day)
    if start is None or end is None:
        return None, None
    if (start_cutoff - start[0]).days > 7:
        return None, start[0].isoformat()

    window = [(d, v) for d, v in points if start[0] <= d <= target_day]
    if not window:
        return None, start[0].isoformat()

    peak = window[0][1]
    worst = 0.0
    for _, nav in window:
        peak = max(peak, nav)
        if peak > 0:
            worst = min(worst, nav / peak - 1.0)
    return worst, start[0].isoformat()

def main():
    coverage = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    eligible = [
        row for row in coverage.get("results", [])
        if row.get("target_date_found") is True
        and not row.get("error")
        and row.get("instrument_id") is not None
    ]

    results = []
    total = len(eligible)
    print(f"ELIGIBLE: {total}")

    for index, row in enumerate(eligible, 1):
        isin = row.get("isin")
        instrument_id = row.get("instrument_id")
        result = {
            "isin": isin,
            "instrument_id": instrument_id,
            "reference_date": TARGET.isoformat(),
            "source": "Erste Market historical NAV chart",
            "target_nav": None,
            "target_nav_date": None,
            "return_ytd": None,
            "return_1y": None,
            "return_5y_cagr": None,
            "max_drawdown_1y": None,
            "volatility_1y": None,
            "start_date_ytd": None,
            "start_date_1y": None,
            "start_date_5y": None,
            "start_date_drawdown_1y": None,
            "status": "PENDING",
            "error": None,
        }

        try:
            points = fetch_series(instrument_id)
            as_of = [(d, v) for d, v in points if d <= TARGET]
            target_point = next(
                ((d, v) for d, v in reversed(as_of) if d == TARGET),
                None,
            )
            if target_point is None:
                result["status"] = "TARGET_NAV_MISSING_ON_REFETCH"
            else:
                result["target_nav_date"] = target_point[0].isoformat()
                result["target_nav"] = target_point[1]

                ytd, ytd_date = relative_return(
                    points, TARGET, date(2025, 12, 31)
                )
                one_year, one_year_date = relative_return(
                    points, TARGET, date(2025, 10, 7)
                )
                five_year, five_year_date = cagr_5y(points, TARGET)
                drawdown, drawdown_date = max_drawdown_1y(points, TARGET)

                result.update({
                    "return_ytd": ytd,
                    "start_date_ytd": ytd_date,
                    "return_1y": one_year,
                    "start_date_1y": one_year_date,
                    "return_5y_cagr": five_year,
                    "start_date_5y": five_year_date,
                    "max_drawdown_1y": drawdown,
                    "start_date_drawdown_1y": drawdown_date,
                    "status": "METRICS_CALCULATED",
                })
        except Exception as exc:
            result["status"] = "FETCH_OR_PARSE_ERROR"
            result["error"] = f"{type(exc).__name__}: {exc}"

        results.append(result)
        if index % 25 == 0 or index == total:
            print(f"PROGRESS: {index}/{total}")
        time.sleep(0.25)

    status_counts = {}
    for row in results:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

    output = {
        "artifact": "historical_nav_metrics_old892_20261007",
        "reference_date": TARGET.isoformat(),
        "input_coverage_artifact": COVERAGE_PATH.name,
        "eligible_input_count": total,
        "result_count": len(results),
        "status_counts": status_counts,
        "metric_definitions": {
            "return_ytd": "NAV on 2026-10-07 / NAV on or before 2025-12-31 - 1",
            "return_1y": "NAV on 2026-10-07 / NAV on or before 2025-10-07 - 1; start point must be within 7 days before cutoff",
            "return_5y_cagr": "NAV-derived annualized return using a start NAV on or before 2021-10-07; start point must be within 7 days before cutoff",
            "max_drawdown_1y": "Worst NAV-to-running-peak decline in the one-year window through 2026-10-07; start point must be within 7 days before cutoff",
            "volatility_1y": "Not calculated; deliberately null",
        },
        "limitations": [
            "Metrics are derived from historical NAV and are not necessarily identical to provider-published metrics.",
            "No same-date 931-fund cross-sectional rank is calculated.",
            "NAV-derived volatility is not estimated.",
            "Only observations on or before the reference date are used.",
            "This artifact does not create or backfill rank history.",
        ],
        "historical_backfill": False,
        "rank_history_write": False,
        "production_decisions_modified": False,
        "trade_authority": "NONE",
        "forced_fill": False,
        "results": results,
    }

    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"OUTPUT: {OUTPUT_PATH}")
    print(f"STATUS_COUNTS: {json.dumps(status_counts, ensure_ascii=False)}")
    print("RANK_HISTORY_MODIFIED: False")
    print("PRODUCTION_DECISIONS_MODIFIED: False")
    print("TRADE_AUTHORITY: NONE")
    print("FORCED_FILL: False")

if __name__ == "__main__":
    main()
