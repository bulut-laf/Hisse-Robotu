
from __future__ import annotations
import argparse, json
from datetime import date
from pathlib import Path

from backend.app.analysis.fin_prod_v5_short_term_context_adapter import (
    build_short_term_canonical_context,
    save_short_term_canonical_context,
)

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="TUPRS")
    p.add_argument("--as-of-date", required=True)
    p.add_argument(
        "--data-root",
        default="backend/data",
    )
    p.add_argument("--output")
    args = p.parse_args()

    symbol = args.symbol.strip().upper()
    as_of = date.fromisoformat(args.as_of_date)
    output = args.output or (
        f"backend/data/financial_intelligence/"
        f"{symbol}_short_term_canonical_context.json"
    )

    payload = build_short_term_canonical_context(
        symbol=symbol,
        as_of_date=as_of,
        data_root=Path(args.data_root),
    )
    path = save_short_term_canonical_context(payload, output_path=output)

    summary = {
        "status": payload["status"],
        "symbol": payload["symbol"],
        "as_of_date": payload["as_of_date"],
        "data_quality": payload["data_quality"],
        "blockers": payload["blockers"],
        "warnings": payload["warnings"],
        "schema_version": payload["schema_version"],
        "result": str(path),
    }
    print(json.dumps(summary, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
