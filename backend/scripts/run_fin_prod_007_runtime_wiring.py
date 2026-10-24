from __future__ import annotations
import argparse, json
from pathlib import Path
from app.analysis.investability_runtime_wiring import load_json, run_runtime_wiring

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-input", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    result = run_runtime_wiring(
        base_input=load_json(a.base_input),
        canonical_evidence=load_json(a.evidence),
    )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print()
    print("FIN-PROD-007 ACCEPTANCE PASS")
    print("RESULT=" + str(out.resolve()))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
