from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys

REPO_BACKEND = Path(__file__).resolve().parents[1]
if str(REPO_BACKEND) not in sys.path:
    sys.path.insert(0, str(REPO_BACKEND))

from app.analysis.financial_intelligence_acceptance import run_financial_intelligence_acceptance


def dec(value):
    return None if value is None else Decimal(value)


def main() -> int:
    p = argparse.ArgumentParser(description="Financial Intelligence V1 production acceptance runner")
    p.add_argument("--xls", required=True)
    p.add_argument("--as-of")
    p.add_argument("--price")
    p.add_argument("--total-shares")
    p.add_argument("--diluted-shares")
    p.add_argument("--free-float-ratio")
    p.add_argument("--effective-free-float-ratio")
    p.add_argument("--major-shareholder-ratio")
    p.add_argument("--json-out")
    args = p.parse_args()

    as_of = datetime.fromisoformat(args.as_of) if args.as_of else None
    result = run_financial_intelligence_acceptance(
        args.xls,
        as_of=as_of,
        price=dec(args.price),
        total_shares=dec(args.total_shares),
        diluted_shares=dec(args.diluted_shares),
        free_float_ratio=dec(args.free_float_ratio),
        effective_free_float_ratio=dec(args.effective_free_float_ratio),
        major_shareholder_ratio=dec(args.major_shareholder_ratio),
    )

    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text, encoding="utf-8")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
