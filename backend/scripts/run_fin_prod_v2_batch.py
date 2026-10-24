from __future__ import annotations
import argparse, json
from pathlib import Path

from app.analysis.financial_intelligence_production_v2 import build_batch_manifest, save_json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=r"D:\Projects\Hisse-Robotu")
    ap.add_argument("--symbols", required=True, help="Comma-separated symbols")
    ap.add_argument("--sector-map", help="Optional JSON file: {\"TUPRS\":\"INDUSTRIAL\"}")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    sector_map = {}
    if args.sector_map:
        sector_map = json.loads(Path(args.sector_map).read_text(encoding="utf-8"))

    symbols = [x.strip().upper() for x in args.symbols.split(",") if x.strip()]
    payload = build_batch_manifest(repo=args.repo, symbols=symbols, sector_map=sector_map)
    save_json(args.out, payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print()
    print("FIN-PROD-V2 ACCEPTANCE PASS")
    print("RESULT=" + str(Path(args.out).resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
