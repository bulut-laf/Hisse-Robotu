from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.analysis.financial_intelligence_live_pipeline_v3 import (
    build_live_batch,
    load_sector_map,
    save_json,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=r"D:\Projects\Hisse-Robotu")
    ap.add_argument("--symbols", default="")
    ap.add_argument("--sector-map")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    symbols = tuple(
        x.strip().upper()
        for x in args.symbols.split(",")
        if x.strip()
    )

    payload = build_live_batch(
        repo=args.repo,
        symbols=symbols or None,
        sector_map=load_sector_map(args.sector_map),
    )
    save_json(args.out, payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print()
    print("FIN-PROD-V3 ACCEPTANCE PASS")
    print("RESULT=" + str(Path(args.out).resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
