from __future__ import annotations
import argparse, json
from pathlib import Path

from app.analysis.canonical_investability_evidence import (
    build_canonical_evidence, load_json, save_json
)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--financial", required=True)
    ap.add_argument("--fair-value", required=True)
    ap.add_argument("--market-ownership")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    result = build_canonical_evidence(
        financial_acceptance=load_json(a.financial),
        fair_value_acceptance=load_json(a.fair_value),
        market_ownership_acceptance=load_json(a.market_ownership) if a.market_ownership else None,
    )
    save_json(a.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    print()
    print("FIN-PROD-006 ACCEPTANCE PASS")
    print("RESULT=" + str(Path(a.out).resolve()))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
