from __future__ import annotations

from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.funds.international.erste_hungary_comparison import (
    fetch_single_fund_comparison,
)


def main() -> int:
    capture_dir = ROOT / "_discovery" / "erste_hungary"
    sample_isin = "HU0000704200"

    fund = fetch_single_fund_comparison(
        sample_isin,
        timeout_seconds=40.0,
    )

    payload = {
        "isin": fund.isin,
        "name": fund.name,
        "fund_manager": fund.fund_manager,
        "inception_date": fund.inception_date.isoformat() if fund.inception_date else None,
        "currency": fund.currency,
        "return_ytd": str(fund.return_ytd) if fund.return_ytd is not None else None,
        "return_1y": str(fund.return_1y) if fund.return_1y is not None else None,
        "return_5y": str(fund.return_5y) if fund.return_5y is not None else None,
        "volatility_1y": str(fund.volatility_1y) if fund.volatility_1y is not None else None,
        "volatility_3y": str(fund.volatility_3y) if fund.volatility_3y is not None else None,
        "volatility_5y": str(fund.volatility_5y) if fund.volatility_5y is not None else None,
        "max_drawdown_1y": str(fund.max_drawdown_1y) if fund.max_drawdown_1y is not None else None,
        "max_drawdown_5y": str(fund.max_drawdown_5y) if fund.max_drawdown_5y is not None else None,
        "nav": str(fund.nav) if fund.nav is not None else None,
        "nav_date": fund.nav_date.isoformat() if fund.nav_date else None,
        "net_asset_value": str(fund.net_asset_value) if fund.net_asset_value is not None else None,
        "category_raw": fund.category_raw,
        "risk_raw": fund.risk_raw,
    }

    out = capture_dir / "comparison_scoped_sample_latest.json"
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("SAMPLE=" + json.dumps(payload, ensure_ascii=False))
    print("OUTPUT_JSON=_discovery/erste_hungary/comparison_scoped_sample_latest.json")
    print("STORE_MUTATION=NO")
    print("STATUS_FINAL=SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())