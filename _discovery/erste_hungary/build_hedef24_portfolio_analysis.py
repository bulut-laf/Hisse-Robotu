import csv
import json
from pathlib import Path
from decimal import Decimal

D = Path("_discovery/erste_hungary")
SRC = D / "hedef24_comparison_report_20261027.json"
OUT_JSON = D / "hedef24_portfolio_analysis_20261027.json"
OUT_CSV = D / "hedef24_portfolio_analysis_20261027.csv"

# (Guncel HUF degeri, ekran goruntusundeki kar/zarar yuzdesi)
holdings = {
    "HU0000703830": (4559062, 25.00),
    "AT0000A09GU1": (3774379, 54.83),
    "AT0000673389": (1431479, 57.66),
    "LU2334866550": (863218, 20.79),
    "HU0000723572": (799626, 8.02),
    "LU0293313671": (784995, 9.85),
    "LU0161304786": (795789, 11.36),
    "LU2614689482": (778681, 8.97),
    "LU0565135745": (769984, 7.74),
    "AT0000A0FSN4": (472799, 30.71),
    "HU0000708656": (444747, 37.71),
    "HU0000712492": (286062, 10.08),
    "LU1387832436": (198292, 8.23),
    "HU0000714191": (185457, 1.65),
    "AT0000A00G88": (135082, 36.47),
    "AT0000627476": (114411, 14.83),
    "AT0000673165": (102991, 41.24),
    "HU0000705306": (53790, 7.59),
    "AT0000A18XC5": (54286, 9.39),
    "HU0000740691": (51029, 2.06),
    "HU0000732011": (26056, 30.29),
    "AT0000A2BYF3": (12379, -2.44),
    "AT0000A3PA11": (5624, 0.60),
    "AT0000A09GW7": (4672, 31.26),
}

if not SRC.exists():
    raise SystemExit(f"MISSING_SOURCE={SRC}")

data = json.loads(SRC.read_text(encoding="utf-8-sig"))
funds = data.get("funds")
if not isinstance(funds, list):
    raise SystemExit("INVALID_COMPARISON_SCHEMA")

by_isin = {str(x.get("isin", "")).upper(): x for x in funds}
if len(by_isin) != 24:
    raise SystemExit(f"EXPECTED_24_FUNDS_GOT={len(by_isin)}")

if set(by_isin) != set(holdings):
    raise SystemExit(
        f"ISIN_MISMATCH missing={sorted(set(by_isin)-set(holdings))} "
        f"extra={sorted(set(holdings)-set(by_isin))}"
    )

total = sum(v[0] for v in holdings.values())
rows = []

for isin, fund in by_isin.items():
    value, shown_return = holdings[isin]
    weight = Decimal(value) * Decimal("100") / Decimal(total)

    raw_dd = fund.get("max_drawdown_1y_percent")
    if raw_dd not in (None, ""):
        dd = Decimal(str(raw_dd))
        dd_basis = "1-year"
    else:
        raw_dd = fund.get("short_period_max_drawdown_percent")
        dd = Decimal(str(raw_dd)) if raw_dd not in (None, "") else None
        dd_basis = "short-period-only" if dd is not None else "unavailable"

    if dd_basis == "1-year":
        review = "RISK_REVIEW"
    elif dd_basis == "short-period-only":
        review = "SHORT_HISTORY_REVIEW"
    else:
        review = "DATA_REVIEW"

    rows.append({
        "isin": isin,
        "fund_name": fund.get("fund_name", ""),
        "value_huf": value,
        "portfolio_weight_pct": round(float(weight), 4),
        "reported_return_pct": shown_return,
        "max_drawdown_pct": float(dd) if dd is not None else "",
        "drawdown_basis": dd_basis,
        "latest_nav_date": fund.get("latest_nav_date", ""),
        "analysis_status": fund.get("analysis_status", ""),
        "review_priority": review,
        "decision": "PENDING_FULL_PORTFOLIO_REVIEW",
    })

rows.sort(key=lambda r: r["value_huf"], reverse=True)

payload = {
    "report": "HEDEF24_PORTFOLIO_ANALYSIS_V1",
    "reference_date": "2026-10-27",
    "portfolio_count": len(rows),
    "estimated_total_value_huf": total,
    "duett_value_huf": holdings["HU0000703830"][0],
    "duett_reported_return_pct": holdings["HU0000703830"][1],
    "source_note": (
        "Position values and displayed returns were transcribed from user-provided "
        "screenshots; Duett value and return were supplied separately by the user."
    ),
    "limitations": [
        "Screenshot valuation dates may differ.",
        "Displayed return periods have not been independently verified.",
        "No fund holdings overlap or fee comparison has yet been performed.",
        "This report does not make automatic sell/hold decisions."
    ],
    "funds": rows,
}

OUT_JSON.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
)
with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print("PORTFOLIO_ANALYSIS=PASS")
print(f"FUNDS={len(rows)}")
print(f"ESTIMATED_TOTAL_HUF={total}")
print(f"DUETT_VALUE_HUF={holdings['HU0000703830'][0]}")
print(f"DUETT_RETURN_PCT={holdings['HU0000703830'][1]:.2f}")
print(f"JSON_REPORT={OUT_JSON}")
print(f"CSV_REPORT={OUT_CSV}")
print("\nTOP_10_BY_VALUE")
for r in rows[:10]:
    dd = "N/A" if r["max_drawdown_pct"] == "" else f'{r["max_drawdown_pct"]:.2f}% [{r["drawdown_basis"]}]'
    print(
        f'{r["fund_name"]}|{r["value_huf"]}|'
        f'weight={r["portfolio_weight_pct"]:.2f}%|'
        f'return={r["reported_return_pct"]:.2f}%|drawdown={dd}'
    )
