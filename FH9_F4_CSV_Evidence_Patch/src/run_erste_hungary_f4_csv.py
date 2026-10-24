from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.app.funds.international.erste_hungary_f4_csv import (
    TARGET_ISINS, BAMOSZ_DOWNLOAD_URL, parse_bamosz_csv, fund_size_change
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "_discovery" / "erste_hungary" / "f4_csv_evidence"
OUT.mkdir(parents=True, exist_ok=True)
summary = []
for isin in TARGET_ISINS:
    request = Request(
        BAMOSZ_DOWNLOAD_URL,
        data=urlencode({"isin": isin, "separator": ";"}).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "Hisse-Robotu-FH9-F4-evidence/1.0"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            raw = response.read()
            status = response.status
            content_type = response.headers.get("Content-Type", "")
        if status != 200:
            raise RuntimeError(f"HTTP_{status}")
        # Preserve original response bytes as evidence before parsing.
        (OUT / f"{isin}.csv").write_bytes(raw)
        parsed = parse_bamosz_csv(raw, isin)
        payload = {
            "isin": isin, "status": "PARSED" if len(parsed.rows) >= 2 else "INSUFFICIENT_VALID_DAILY_ROWS",
            "http_status": status, "content_type": content_type,
            "download_bytes": parsed.download_bytes, "encoding": parsed.encoding,
            "delimiter": parsed.delimiter, "fund_name": parsed.fund_name,
            "header": list(parsed.header), "valid_daily_rows": len(parsed.rows),
            "first_date": parsed.rows[0].date.isoformat() if parsed.rows else None,
            "latest_date": parsed.rows[-1].date.isoformat() if parsed.rows else None,
            "latest_nav": str(parsed.rows[-1].nav) if parsed.rows else None,
            "fund_size_change_last_two_valid_navs": (
                str(fund_size_change(parsed.rows)) if fund_size_change(parsed.rows) is not None else None
            ),
            "fund_size_change_definition": "(latest_valid_NAV / previous_valid_NAV) - 1",
            "net_flow_ratio": None,
            "net_flow_ratio_status": "UNAVAILABLE_OFFICIAL_NET_INVESTOR_FLOW_NOT_PROVEN",
            "semantic_proxy": False,
            "automatic_trade_authority": "NONE", "trade_authority": "NONE",
            "forced_fill": False,
        }
    except Exception as exc:
        payload = {
            "isin": isin, "status": "FETCH_OR_PARSE_FAILED", "error": f"{type(exc).__name__}:{exc}",
            "net_flow_ratio": None, "semantic_proxy": False,
            "automatic_trade_authority": "NONE", "trade_authority": "NONE", "forced_fill": False,
        }
    (OUT / f"{isin}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary.append(payload)
    print(f"{isin} STATUS={payload['status']} ROWS={payload.get('valid_daily_rows', 0)}")

(OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"SUMMARY={OUT / 'summary.json'}")
print("TRADE_AUTHORITY=NONE")
print("FORCED_FILL=NO")
