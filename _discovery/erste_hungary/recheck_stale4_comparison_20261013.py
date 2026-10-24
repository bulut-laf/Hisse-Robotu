import json
from datetime import datetime, timezone
from pathlib import Path

from backend.app.funds.international.erste_hungary_comparison import (
    fetch_single_fund_comparison,
)

OUTPUT = Path("_discovery/erste_hungary/stale4_comparison_recheck_20261013.json")
ISINS = [
    "LU0011850392",
    "LU0113311731",
    "LU0117895796",
    "LU0823403356",
]

results = []

for isin in ISINS:
    row = {
        "isin": isin,
        "success": False,
        "nav_date": None,
        "nav": None,
        "error": None,
    }

    try:
        fund = fetch_single_fund_comparison(isin, timeout_seconds=30.0)
        row.update({
            "success": True,
            "returned_isin": getattr(fund, "isin", None),
            "nav_date": str(getattr(fund, "nav_date", None))
                if getattr(fund, "nav_date", None) is not None else None,
            "nav": str(getattr(fund, "nav", None)) if getattr(fund, "nav", None) is not None else None,
            "name": getattr(fund, "name", None),
        })
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

    results.append(row)
    print(json.dumps(row, ensure_ascii=False, default=str))

payload = {
    "artifact_type": "STALE4_COMPARISON_RECHECK",
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "results": results,
    "rank_history_write": False,
    "production_decisions_modified": False,
    "trade_authority": "NONE",
    "forced_fill": False,
}

OUTPUT.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(f"OUTPUT: {OUTPUT}")
print("RANK_HISTORY_WRITE: False")
print("PRODUCTION_DECISIONS_MODIFIED: False")
print("TRADE_AUTHORITY: NONE")
print("FORCED_FILL: False")

