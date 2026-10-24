from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.analysis.financial_intelligence_fair_value_acceptance import (
    FairValueAcceptanceError,
    run_fair_value_acceptance,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    result = run_fair_value_acceptance(config)

    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)

    if args.out:
        out = Path(args.out)
    else:
        symbol = result["symbol"]
        out = Path("backend/data/financial_intelligence") / f"{symbol}_fair_value_acceptance.json"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print()
    print("FIN-PROD-004 ACCEPTANCE", result["status"])
    print("RESULT=" + str(out.resolve()))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
