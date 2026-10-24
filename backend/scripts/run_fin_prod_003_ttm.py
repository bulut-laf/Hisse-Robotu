from __future__ import annotations

import argparse, json, sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.analysis.financial_intelligence_ttm_acceptance import run_ttm_market_acceptance


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--xls", action="append", required=True)
    p.add_argument("--market-ownership-json", required=True)
    p.add_argument("--price")
    p.add_argument("--price-date")
    p.add_argument("--as-of")
    p.add_argument("--ebitda-ttm")
    p.add_argument("--json-out")
    a = p.parse_args()

    result = run_ttm_market_acceptance(
        a.xls,
        a.market_ownership_json,
        price=Decimal(a.price) if a.price else None,
        price_date=date.fromisoformat(a.price_date) if a.price_date else None,
        as_of=datetime.fromisoformat(a.as_of) if a.as_of else None,
        ebitda_ttm_override=Decimal(a.ebitda_ttm) if a.ebitda_ttm else None,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if a.json_out:
        Path(a.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json_out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
