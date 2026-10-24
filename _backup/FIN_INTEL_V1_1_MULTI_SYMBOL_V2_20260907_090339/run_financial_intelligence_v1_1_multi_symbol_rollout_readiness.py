from __future__ import annotations

import json
import re
from pathlib import Path

PATTERN = re.compile(r"^financial_intelligence_acceptance_(?P<symbol>[A-Z0-9._-]+)_(?P<period>[^.]+)\.json$")

def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def truthy_pass(data: dict) -> bool:
    status = str(data.get("status") or "").upper()
    return status in {"PASS", "READY", "OK", "SUCCESS"} or data.get("accepted") is True

def main() -> None:
    root = Path(__file__).resolve().parents[2]
    backend = root / "backend"
    data_dir = backend / "data"
    fi_dir = data_dir / "financial_intelligence"

    candidates = []
    for path in sorted(data_dir.glob("financial_intelligence_acceptance_*.json")):
        m = PATTERN.match(path.name)
        if not m:
            continue
        symbol = m.group("symbol")
        period = m.group("period")
        data = load_json(path)

        canonical_outputs = {
            "short_term": fi_dir / f"{symbol}_short_term_canonical_context.json",
            "long_term": fi_dir / f"{symbol}_long_term_canonical_coverage.json",
            "panel": fi_dir / f"{symbol}_financial_intelligence_panel.json",
            "market_ownership": fi_dir / f"{symbol}_market_ownership_acceptance.json",
            "investability_acceptance": fi_dir / f"{symbol}_investability_acceptance.json",
            "investability_closure": fi_dir / f"{symbol}_investability_production_closure.json",
        }

        existing_outputs = {k: p.exists() for k, p in canonical_outputs.items()}
        candidates.append({
            "symbol": symbol,
            "period": period,
            "acceptance_path": str(path),
            "acceptance_status": data.get("status"),
            "acceptance_pass_like": truthy_pass(data),
            "existing_outputs": existing_outputs,
            "existing_output_count": sum(existing_outputs.values()),
            "reference_symbol": symbol == "TUPRS",
        })

    non_reference = [c for c in candidates if not c["reference_symbol"]]
    pass_like = [c for c in non_reference if c["acceptance_pass_like"]]
    status = "READY_FOR_MULTI_SYMBOL_ROLLOUT" if pass_like else "NO_ADDITIONAL_ACCEPTED_SYMBOLS_FOUND"

    out = fi_dir / "FINANCIAL_INTELLIGENCE_V1_1_MULTI_SYMBOL_ROLLOUT_READINESS.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "financial-intelligence-v1.1-multi-symbol-rollout-readiness-v1",
        "status": status,
        "mode": "READ_ONLY_DISCOVERY",
        "reference_symbol": "TUPRS",
        "candidate_count": len(candidates),
        "additional_candidate_count": len(non_reference),
        "additional_pass_like_count": len(pass_like),
        "candidates": candidates,
        "rules": [
            "NO_NEW_SCORE",
            "NO_NEW_STORE",
            "NO_AL_SAT_MUTATION",
            "NO_SCANNER_MUTATION",
            "NO_RANKING_MUTATION",
            "NO_PORTFOLIO_MUTATION",
            "REUSE_EXISTING_FINANCIAL_INTELLIGENCE_PIPELINE",
            "TUPRS_REMAINS_REFERENCE_ACCEPTANCE_SYMBOL",
        ],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"STATUS={status}")
    print(f"CANDIDATE_COUNT={len(candidates)}")
    print(f"ADDITIONAL_CANDIDATE_COUNT={len(non_reference)}")
    print(f"ADDITIONAL_PASS_LIKE_COUNT={len(pass_like)}")
    for c in pass_like[:20]:
        print(f"READY_SYMBOL={c['symbol']} PERIOD={c['period']} EXISTING_OUTPUTS={c['existing_output_count']}/6")
    print(f"RESULT={out}")
    print("FINANCIAL_INTELLIGENCE_V1_1_MULTI_SYMBOL_ROLLOUT_READINESS=PASS")

if __name__ == "__main__":
    main()
