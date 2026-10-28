import csv
import json
from pathlib import Path
from decimal import Decimal, InvalidOperation

D = Path("_discovery/erste_hungary")
PORTFOLIO = D / "hedef24_portfolio_prepared_20261027.json"
RECOVERY = D / "hedef24_f3_nav_recovery_20261027.json"
SHORT = D / "hedef24_short_history_HU0000740691_20261027.json"

OUT_JSON = D / "hedef24_comparison_report_20261027.json"
OUT_CSV = D / "hedef24_comparison_report_20261027.csv"

def load_json(path):
    if not path.exists():
        raise SystemExit(f"MISSING_FILE={path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))

def extract_rows(data, label):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "isin" in data:
            return [data]
        for value in data.values():
            if isinstance(value, list) and value and isinstance(value[0], dict) and "isin" in value[0]:
                return value
    raise SystemExit(f"UNRECOGNIZED_SCHEMA={label}")

def first_value(row, *keys):
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return value
    return ""

def as_decimal(value):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None

portfolio_data = load_json(PORTFOLIO)
portfolio_rows = extract_rows(portfolio_data, "portfolio")
recovery_rows = extract_rows(load_json(RECOVERY), "recovery")
short = load_json(SHORT)

portfolio_by_isin = {}
for row in portfolio_rows:
    isin = str(row.get("isin", "")).strip().upper()
    if isin:
        portfolio_by_isin[isin] = row

recovery_by_isin = {
    str(row.get("isin", "")).strip().upper(): row
    for row in recovery_rows
    if row.get("isin")
}

short_isin = str(short.get("isin", "")).strip().upper()
if short_isin:
    recovery_by_isin[short_isin] = {
        "isin": short_isin,
        "status": short.get("status", "SHORT_HISTORY_ANALYZED"),
        "reason": short.get("one_year_status", "UNAVAILABLE_INSUFFICIENT_HISTORY"),
        "max_drawdown_1y": None,
        "latest_date": short.get("latest_observation_date"),
        "freshness_days": None,
        "series_count": short.get("observation_count"),
        "short_period_return_percent": short.get("period_return_percent"),
        "short_period_max_drawdown_percent": short.get("max_drawdown_percent"),
        "short_period_start": short.get("first_observation_date"),
        "short_period_end": short.get("latest_observation_date"),
    }

report = []
for slot, (isin, p) in enumerate(portfolio_by_isin.items(), start=1):
    r = recovery_by_isin.get(isin, {})
    name = first_value(
        p, "name", "fund_name", "fund", "title", "display_name", "fundName"
    )
    if isinstance(name, dict):
        name = first_value(name, "name", "title", "value")

    one_year_dd = as_decimal(r.get("max_drawdown_1y"))
    short_dd = as_decimal(r.get("short_period_max_drawdown_percent"))
    short_return = as_decimal(r.get("short_period_return_percent"))

    if one_year_dd is not None:
        status = "ONE_YEAR_DRAWDOWN_AVAILABLE"
        dd_pct = one_year_dd * Decimal("100")
        comparison_note = "1-year maximum drawdown"
    elif short_dd is not None:
        status = "SHORT_HISTORY_ONLY"
        dd_pct = short_dd
        comparison_note = "Short period only; not directly comparable to 1-year results"
    else:
        status = "DATA_REVIEW_REQUIRED"
        dd_pct = None
        comparison_note = "No usable drawdown value found"

    report.append({
        "slot": first_value(p, "slot", "position", "number") or slot,
        "isin": isin,
        "fund_name": name,
        "analysis_status": status,
        "recovery_status": r.get("status", "NO_RECOVERY_RECORD"),
        "reason": r.get("reason", ""),
        "latest_nav_date": r.get("latest_date", ""),
        "freshness_days": r.get("freshness_days", ""),
        "series_count": r.get("series_count", ""),
        "max_drawdown_1y_decimal": str(one_year_dd) if one_year_dd is not None else "",
        "max_drawdown_1y_percent": str(one_year_dd * 100) if one_year_dd is not None else "",
        "short_period_start": r.get("short_period_start", ""),
        "short_period_end": r.get("short_period_end", ""),
        "short_period_return_percent": str(short_return) if short_return is not None else "",
        "short_period_max_drawdown_percent": str(short_dd) if short_dd is not None else "",
        "comparison_note": comparison_note,
        "decision": "PENDING_PORTFOLIO_AND_OVERLAP_ANALYSIS",
    })

if len(portfolio_by_isin) != 24:
    raise SystemExit(f"EXPECTED_24_PORTFOLIO_ISINS_GOT={len(portfolio_by_isin)}")

available_1y = sum(1 for row in report if row["max_drawdown_1y_percent"] != "")
short_only = sum(1 for row in report if row["analysis_status"] == "SHORT_HISTORY_ONLY")
needs_review = sum(1 for row in report if row["analysis_status"] == "DATA_REVIEW_REQUIRED")

payload = {
    "report": "HEDEF24_COMPARISON_REPORT_V1",
    "reference_date": "2026-10-27",
    "portfolio_count": len(report),
    "one_year_drawdown_available": available_1y,
    "short_history_only": short_only,
    "data_review_required": needs_review,
    "decision_status": "PRELIMINARY_DATA_COMPARISON_NOT_A_SELL_HOLD_DECISION",
    "notes": [
        "The one-year drawdown is only reported where F3 supplied a qualified value.",
        "Short-history figures are kept in separate fields and are not ranked against one-year figures.",
        "No portfolio weights, purchase costs, taxes, fees, or fund overlap have been inferred.",
        "No production store, TEFAS data, or AL-SAT behavior was changed."
    ],
    "funds": report,
}

OUT_JSON.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

columns = list(report[0].keys()) if report else []
with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    writer.writerows(report)

print("HEDEF24_COMPARISON=PASS")
print(f"PORTFOLIO_COUNT={len(report)}")
print(f"ONE_YEAR_DRAWDOWN_AVAILABLE={available_1y}")
print(f"SHORT_HISTORY_ONLY={short_only}")
print(f"DATA_REVIEW_REQUIRED={needs_review}")
print(f"JSON_REPORT={OUT_JSON}")
print(f"CSV_REPORT={OUT_CSV}")
print("\n=== FUND COMPARISON ===")
for row in report:
    dd = row["max_drawdown_1y_percent"] or row["short_period_max_drawdown_percent"] or "N/A"
    print(f"{row['isin']}|{row['fund_name']}|{row['analysis_status']}|drawdown_pct={dd}")

