from __future__ import annotations

import argparse, json, sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.data.market_ownership_canonical import load_market_ownership_input, from_dict
from app.analysis.financial_intelligence_market_acceptance import run_market_ownership_acceptance


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--xls", action="append", required=True, help="Repeat for multiple KAP periods")
    p.add_argument("--input-json", required=True)
    p.add_argument("--price", help="Override price_try in JSON")
    p.add_argument("--price-date", help="Override price_date")
    p.add_argument("--as-of")
    p.add_argument("--ebitda-ttm")
    p.add_argument("--fcf-ttm")
    p.add_argument("--json-out")
    a = p.parse_args()

    raw = json.loads(Path(a.input_json).read_text(encoding="utf-8"))
    if a.price is not None:
        raw["price_try"] = a.price
    if a.price_date is not None:
        raw["price_date"] = a.price_date
    canonical = from_dict(raw)

    result = run_market_ownership_acceptance(
        a.xls,
        canonical,
        as_of=datetime.fromisoformat(a.as_of) if a.as_of else None,
        ebitda_ttm=Decimal(a.ebitda_ttm) if a.ebitda_ttm else None,
        fcf_ttm=Decimal(a.fcf_ttm) if a.fcf_ttm else None,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if a.json_out:
        Path(a.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json_out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
