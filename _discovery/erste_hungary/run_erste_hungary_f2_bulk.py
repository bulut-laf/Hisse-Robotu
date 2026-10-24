from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.request import build_opener, HTTPCookieProcessor, Request
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.app.funds.evidence_mapper import map_fund_evidence
from backend.app.funds.analysis_engine import analyze_fund
from backend.app.funds.international.erste_hungary_f2_bridge import (
    F2_BRIDGE_VERSION,
    build_f1_f2_f3_input,
    derive_f2_returns,
)
from backend.app.funds.international.erste_hungary_f3_bridge import (
    category_volatility_percentiles,
)

DISC = ROOT / "_discovery" / "erste_hungary"
META = DISC / "bulk_metadata_daily_2026-09-25.jsonl"
F1 = DISC / "f1_evidence_bridge_v1_latest.json"
CACHE = DISC / "f2_bulk_progress_v1.jsonl"
OUTPUT = DISC / "f1_f2_f3_evidence_v1_latest.json"
SUMMARY = DISC / "f1_f2_f3_evidence_v1_summary_latest.json"

BASE = "https://www.erstemarket.hu"
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 Hisse-Robotu-Erste-F2-Bulk-v1",
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
}

CATEGORY_MAP = {
    "R\u00e9szv\u00e9ny": "EQUITY",
    "K\u00f6tv\u00e9ny": "BOND",
    "Abszol\u00fat hozam\u00fa": "ABSOLUTE_RETURN",
    "Vegyes": "MIXED",
    "P\u00e9nzpiac": "MONEY_MARKET",
    "Nyersanyag": "COMMODITY",
    "Ingatlan": "REAL_ESTATE",
    "Alapok alapja": "FUND_OF_FUNDS",
    "Sz\u00e1rmaztatott": "DERIVATIVE",
}

meta_rows = [
    json.loads(x)
    for x in META.read_text(encoding="utf-8").splitlines()
    if x.strip()
]
f1_rows = json.loads(F1.read_text(encoding="utf-8"))

for row in meta_rows:
    row["category_normalized"] = CATEGORY_MAP.get(row.get("category_raw"))

meta_by_isin = {str(r["isin"]).upper(): r for r in meta_rows}
vol_pct = category_volatility_percentiles(meta_rows)

existing = {}
if CACHE.exists():
    for line in CACHE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        existing[rec["isin"]] = rec

print(f"TOTAL_TARGET={len(f1_rows)}")
print(f"RESUME_EXISTING={len(existing)}")

jar = CookieJar()
opener = build_opener(HTTPCookieProcessor(jar))


def fetch(url: str, *, referer: str | None = None, ajax: bool = False) -> str:
    headers = dict(COMMON_HEADERS)

    if referer:
        headers["Referer"] = referer

    if ajax:
        headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
        headers["X-Requested-With"] = "XMLHttpRequest"

    req = Request(url, headers=headers)

    with opener.open(req, timeout=45) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_instrument_id(html: str) -> str | None:
    match = re.search(
        r'<div[^>]*class=["\'][^"\']*simpleChartContainer[^"\']*fund[^"\']*["\'][^>]*'
        r'instrument-id=["\'](\d+)["\']',
        html,
        flags=re.I,
    )
    if match:
        return match.group(1)

    match = re.search(r'instrument-id=["\'](\d+)["\']', html, flags=re.I)

    return match.group(1) if match else None


def points_from_chart(obj: dict):
    points = []

    for item in obj.get("series") or []:
        if not isinstance(item, list) or len(item) < 2:
            continue

        ts_ms, price_raw = item[0], item[1]

        try:
            dt = datetime.fromtimestamp(float(ts_ms) / 1000, tz=timezone.utc)
            price = Decimal(str(price_raw))
        except Exception:
            continue

        points.append((dt, price))

    points.sort(key=lambda item: item[0])
    return points


def append_progress(rec: dict):
    with CACHE.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


success = 0
failure = 0

for idx, f1 in enumerate(f1_rows, start=1):
    isin = str(f1["isin"]).upper()

    if isin in existing and existing[isin].get("status") == "SUCCESS":
        success += 1
        continue

    comparison = (
        BASE
        + "/befektetesi_alapok/osszehasonlitas?funds="
        + isin
    )

    try:
        html = fetch(comparison)
        instrument_id = parse_instrument_id(html)

        if not instrument_id:
            raise ValueError("INSTRUMENT_ID_NOT_FOUND")

        chart_url = BASE + "/funds/chart/" + instrument_id
        raw = fetch(
            chart_url,
            referer=comparison,
            ajax=True,
        )
        obj = json.loads(raw)

        returned_isin = str(obj.get("isin") or "").strip().upper()

        if returned_isin != isin:
            raise ValueError(
                f"ISIN_MISMATCH:{returned_isin}!={isin}"
            )

        points = points_from_chart(obj)

        if not points:
            raise ValueError("EMPTY_SERIES")

        r1m, r3m, r6m = derive_f2_returns(points)
        latest_dt, latest_nav = points[-1]

        rec = {
            "isin": isin,
            "status": "SUCCESS",
            "instrument_id": instrument_id,
            "series_count": len(points),
            "as_of": latest_dt.date().isoformat(),
            "latest_nav": str(latest_nav),
            "return_1m": None if r1m is None else str(r1m),
            "return_3m": None if r3m is None else str(r3m),
            "return_6m": None if r6m is None else str(r6m),
        }

        success += 1

    except Exception as exc:
        rec = {
            "isin": isin,
            "status": "FAIL",
            "error": f"{type(exc).__name__}:{exc}",
        }

        failure += 1

    existing[isin] = rec
    append_progress(rec)

    if idx % 25 == 0 or idx == len(f1_rows):
        print(
            f"PROGRESS={idx}/{len(f1_rows)}"
            f"|SUCCESS={success}|FAIL={failure}"
        )

    time.sleep(0.05)


rows = []
f2_counts = Counter()
f3_counts = Counter()
class_counts = Counter()
eligibility_counts = Counter()
trade_counts = Counter()

f2_available = 0
f2_unavailable = 0

for f1 in f1_rows:
    isin = str(f1["isin"]).upper()
    meta = meta_by_isin[isin]
    cache = existing.get(isin, {})

    r1 = cache.get("return_1m")
    r3 = cache.get("return_3m")
    r6 = cache.get("return_6m")

    r1d = None if r1 is None else Decimal(str(r1))
    r3d = None if r3 is None else Decimal(str(r3))
    r6d = None if r6 is None else Decimal(str(r6))

    dd_raw = meta.get("max_drawdown_1y")
    dd = (
        None
        if dd_raw in (None, "", "-")
        else Decimal(str(dd_raw))
    )

    value = build_f1_f2_f3_input(
        isin=isin,
        category_id=f1["category_id"],
        category_rank_percentile=Decimal(
            str(f1["category_rank_percentile"])
        ),
        category_rank_change=int(f1["category_rank_change"]),
        return_1m=r1d,
        return_3m=r3d,
        return_6m=r6d,
        volatility_percentile=vol_pct.get(isin),
        max_drawdown_1y=dd,
    )

    mapped = map_fund_evidence(value)

    f2 = next(
        item for item in mapped.evidence
        if item.family == "F2"
    )
    f3 = next(
        item for item in mapped.evidence
        if item.family == "F3"
    )

    result = analyze_fund(mapped)

    f2_state = (
        f2.state.value
        if hasattr(f2.state, "value")
        else str(f2.state)
    )
    f3_state = (
        f3.state.value
        if hasattr(f3.state, "value")
        else str(f3.state)
    )

    f2_counts[f2_state] += 1
    f3_counts[f3_state] += 1

    classification = (
        result.classification.value
        if hasattr(result.classification, "value")
        else str(result.classification)
    )

    class_counts[classification] += 1
    eligibility_counts[str(result.eligibility_reason)] += 1
    trade_counts[str(result.automatic_trade_authority)] += 1

    if f2_state == "UNAVAILABLE":
        f2_unavailable += 1
    else:
        f2_available += 1

    rows.append({
        "isin": isin,
        "canonical_fund_id": result.canonical_fund_id,
        "category_id": result.category_id,
        "as_of": cache.get("as_of"),
        "instrument_id": cache.get("instrument_id"),
        "return_1m": r1,
        "return_3m": r3,
        "return_6m": r6,
        "f1_state": f1["f1_state"],
        "f2_state": f2_state,
        "f3_state": f3_state,
        "classification": classification,
        "eligibility_reason": result.eligibility_reason,
        "automatic_trade_authority": result.automatic_trade_authority,
        "forced_fill": result.forced_fill,
    })


OUTPUT.write_text(
    json.dumps(rows, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

summary = {
    "version": F2_BRIDGE_VERSION,
    "result_count": len(rows),
    "fetch_success": success,
    "fetch_failure": failure,
    "f2_available": f2_available,
    "f2_unavailable": f2_unavailable,
    "f2_state_counts": dict(f2_counts),
    "f3_state_counts": dict(f3_counts),
    "class_counts": dict(class_counts),
    "eligibility_counts": dict(eligibility_counts),
    "trade_authority_counts": dict(trade_counts),
}

SUMMARY.write_text(
    json.dumps(summary, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"F2_BRIDGE_VERSION={F2_BRIDGE_VERSION}")
print(f"RESULT_COUNT={len(rows)}")
print(f"FETCH_SUCCESS={success}")
print(f"FETCH_FAILURE={failure}")
print(f"F2_AVAILABLE={f2_available}")
print(f"F2_UNAVAILABLE={f2_unavailable}")
print(
    "F2_STATE_COUNTS="
    + json.dumps(dict(f2_counts), ensure_ascii=False)
)
print(
    "F3_STATE_COUNTS="
    + json.dumps(dict(f3_counts), ensure_ascii=False)
)
print(
    "CLASS_COUNTS="
    + json.dumps(dict(class_counts), ensure_ascii=False)
)
print(
    "ELIGIBILITY_COUNTS="
    + json.dumps(dict(eligibility_counts), ensure_ascii=False)
)
print(
    "TRADE_AUTHORITY_COUNTS="
    + json.dumps(dict(trade_counts), ensure_ascii=False)
)

for row in [
    item for item in rows
    if item["classification"] != "X"
][:25]:
    print(
        "NON_X="
        + row["isin"]
        + "|class=" + row["classification"]
        + "|f1=" + row["f1_state"]
        + "|f2=" + row["f2_state"]
        + "|f3=" + row["f3_state"]
        + "|r1m=" + str(row["return_1m"])
        + "|r3m=" + str(row["return_3m"])
        + "|r6m=" + str(row["return_6m"])
        + "|reason=" + str(row["eligibility_reason"])
    )

print("CACHE=_discovery/erste_hungary/f2_bulk_progress_v1.jsonl")
print("OUTPUT_JSON=_discovery/erste_hungary/f1_f2_f3_evidence_v1_latest.json")
print("SUMMARY_JSON=_discovery/erste_hungary/f1_f2_f3_evidence_v1_summary_latest.json")
print("TEFAS_MUTATION=NO")
print("PRODUCTION_STORE_MUTATION=NO")
print("AL_SAT_MUTATION=NO")
print("FORCED_FILL=NO")
print("TRADE_AUTHORITY=NONE")
print("STATUS_FINAL=SUCCESS")