
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# Direct-script execution bootstrap:
# D:\Projects\Hisse-Robotu\backend\scripts\this_file.py
# must still resolve package imports from repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.analysis.fin_prod_v5_short_term_context_adapter import (
    build_short_term_canonical_context,
    save_short_term_canonical_context,
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="TUPRS")
    p.add_argument("--as-of-date", required=True)
    p.add_argument("--data-root", default="backend/data")
    p.add_argument("--output")
    args = p.parse_args()

    symbol = args.symbol.strip().upper()
    as_of = date.fromisoformat(args.as_of_date)

    data_root = Path(args.data_root)
    if not data_root.is_absolute():
        data_root = PROJECT_ROOT / data_root

    output = args.output
    if output is None:
        output_path = (
            PROJECT_ROOT
            / "backend"
            / "data"
            / "financial_intelligence"
            / f"{symbol}_short_term_canonical_context.json"
        )
    else:
        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path

    payload = build_short_term_canonical_context(
        symbol=symbol,
        as_of_date=as_of,
        data_root=data_root,
    )

    path = save_short_term_canonical_context(
        payload,
        output_path=output_path,
    )

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
