from __future__ import annotations
import argparse, json
from pathlib import Path
from app.analysis.long_term_evidence_completion import complete_evidence, load_json, save_json

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--financial", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    result = complete_evidence(
        financial_acceptance=load_json(a.financial),
        existing_evidence=load_json(a.evidence),
    )
    save_json(a.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()
    print("FIN-PROD-008 ACCEPTANCE PASS")
    print("RESULT=" + str(Path(a.out).resolve()))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
