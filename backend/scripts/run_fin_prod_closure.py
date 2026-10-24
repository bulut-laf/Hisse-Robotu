from __future__ import annotations
import argparse, json
from pathlib import Path

from app.analysis.investability_production_closure import load_json, run_closure, save_json

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    result = run_closure(
        base_acceptance=load_json(args.base),
        completed_evidence=load_json(args.evidence),
        data_root=args.data_root,
    )
    save_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()
    print("FIN-PROD-CLOSURE ACCEPTANCE PASS")
    print("RESULT=" + str(Path(args.out).resolve()))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
