from __future__ import annotations
import json, sys
from pathlib import Path
from app.analysis.financial_intelligence_bank_canonical_adapter import adapt_bank_canonical_input

root = Path(sys.argv[1])
source_path = root / "backend" / "data" / "financial_intelligence" / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_EXACT_NUMERIC_BANK_METRIC_EXTRACTION_CANONICAL_GATE.json"
result_path = root / "backend" / "data" / "financial_intelligence" / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_EXACT_DOTTED_KEY_BANK_CANONICAL_GATE.json"

if not source_path.exists():
    raise SystemExit(f"BLOCK10_SOURCE_RESULT_MISSING:{source_path}")

source = json.loads(source_path.read_text(encoding="utf-8-sig"))
flat = source.get("metrics", {})

mapping = {
    "capital_adequacy_ratio": "CAPITAL_ADEQUACY.capital_adequacy_ratio",
    "deposit_growth": "GROWTH_QUALITY.deposit_growth",
    "net_income_growth": "GROWTH_QUALITY.net_income_growth",
}

canonical_facts = {
    dst: flat[src]
    for src, dst in mapping.items()
    if flat.get(src) is not None
}

record = {
    "source_type": source.get("source_type", "KAP"),
    "source_uri": source.get("source_attachment_uri") or source.get("source_uri"),
    "symbol": source.get("symbol", "AKBNK"),
    "sector_model": "BANK",
    "as_of": source.get("as_of"),
    "publication_date": source.get("publication_date"),
    "canonical_facts": canonical_facts,
    "evidence_hash": source.get("evidence_hash"),
}

result = {
    "status": "PASS_FAIL_CLOSED",
    "canonical_facts": canonical_facts,
    "canonical_adapter_status": None,
    "canonical_adapter_blocker": None,
    "canonical_payload_ready": False,
    "production_evidence": False,
    "scoring_ready": False,
    "activation_ready": False,
    "missing_to_zero": False,
    "industrial_threshold_reuse": False,
    "blockers": [],
    "production_mutation": "NO",
    "store_mutation": "NO",
    "al_sat_mutation": "NO",
}

adapted = adapt_bank_canonical_input(record)
status = getattr(adapted, "status", None)
blocker = getattr(adapted, "blocker", None)
payload = getattr(adapted, "payload", None)

result["canonical_adapter_status"] = str(status) if status is not None else None
result["canonical_adapter_blocker"] = str(blocker) if blocker is not None else None
result["canonical_payload_ready"] = bool(payload)

if payload and not blocker:
    result["status"] = "PASS"
    result["production_evidence"] = True
else:
    result["blockers"].append(f"BANK_CANONICAL_ADAPTER_NOT_READY:{blocker}")

result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"STATUS={result['status']}")
print(f"CANONICAL_ADAPTER_STATUS={result['canonical_adapter_status']}")
print(f"CANONICAL_ADAPTER_BLOCKER={result['canonical_adapter_blocker']}")
print(f"CANONICAL_PAYLOAD_READY={result['canonical_payload_ready']}")
print(f"PRODUCTION_EVIDENCE={result['production_evidence']}")
print(f"BLOCKERS={result['blockers']}")
print("SCORING_READY=False")
print("ACTIVATION_READY=False")
print("MISSING_TO_ZERO=False")
print("INDUSTRIAL_THRESHOLD_REUSE=False")
print("PRODUCTION_MUTATION=NO")
print("STORE_MUTATION=NO")
print("AL_SAT_MUTATION=NO")
print(f"RESULT={result_path}")
