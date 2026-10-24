from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.analysis.financial_intelligence_canonical_coverage_v4 import enrich_v3_batch, save_json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=r"D:\Projects\Hisse-Robotu")
    ap.add_argument(
        "--v3-batch",
        default=r"backend\data\financial_intelligence\FIN_PROD_V3_LIVE_BATCH.json",
    )
    ap.add_argument(
        "--out",
        default=r"backend\data\financial_intelligence\FIN_PROD_V4_CANONICAL_COVERAGE.json",
    )
    args = ap.parse_args()

    repo = Path(args.repo)
    v3_path = Path(args.v3_batch)
    if not v3_path.is_absolute():
        v3_path = repo / v3_path
    out = Path(args.out)
    if not out.is_absolute():
        out = repo / out

    if not v3_path.exists():
        raise SystemExit("FIN-PROD-V4 BLOCKED: V3 live batch is missing: " + str(v3_path))

    try:
        v3 = json.loads(v3_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit("FIN-PROD-V4 BLOCKED: invalid V3 batch: " + str(exc))

    if not isinstance(v3, dict) or v3.get("status") != "PASS":
        raise SystemExit("FIN-PROD-V4 BLOCKED: upstream V3 batch is not PASS")

    payload = enrich_v3_batch(repo=repo, v3_batch=v3)
    save_json(out, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print()
    print("FIN-PROD-V4 ACCEPTANCE PASS")
    print("RESULT=" + str(out.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
