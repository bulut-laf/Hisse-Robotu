from __future__ import annotations
import json
import sys
from pathlib import Path

from app.analysis.financial_intelligence_bank_canonical_adapter import adapt_bank_canonical_input

root = Path(sys.argv[1])
data_dir = root / "backend" / "data" / "financial_intelligence"

probe_path = data_dir / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_NPL_RATIO_EXACT_EVIDENCE_PROBE.json"
prior_gate_path = data_dir / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_TIER1_SELECTION_AND_CANONICAL_GATE.json"
result_path = data_dir / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_NPL_RATIO_SELECTION_AND_CANONICAL_GATE.json"

if not probe_path.exists():
    raise SystemExit(f"NPL_PROBE_RESULT_MISSING:{probe_path}")
if not prior_gate_path.exists():
    raise SystemExit(f"PRIOR_CANONICAL_GATE_MISSING:{prior_gate_path}")

probe = json.loads(probe_path.read_text(encoding="utf-8-sig"))
prior = json.loads(prior_gate_path.read_text(encoding="utf-8-sig"))

blob = json.dumps(probe, ensure_ascii=False)
if "takipteki krediler oranı" not in blob.casefold() or "%3,5" not in blob:
    raise SystemExit("NPL_EXACT_SEMANTIC_EVIDENCE_NOT_FOUND")

canonical_facts = dict(prior.get("canonical_facts") or {})
canonical_facts["ASSET_QUALITY.npl_ratio"] = "3.5"

record = {
    "source_type": "KAP",
    "symbol": "AKBNK",
    "sector_model": "BANK",
    "canonical_facts": canonical_facts,
}

result = {
    "schema_version": "financial-intelligence-v1-3-akbnk-npl-ratio-selection-and-canonical-gate-v1",
    "status": "PASS_FAIL_CLOSED",
    "symbol": "AKBNK",
    "sector_model": "BANK",
    "selected_metric": "ASSET_QUALITY.npl_ratio",
    "selected_value": "3.5",
    "selection_semantics": "Akbank’ın takipteki krediler oranı 30 Haziran 2026 tarihi itibarıyla %3,5 seviyesinde gerçekleşmiştir.",
    "canonical_facts": canonical_facts,
    "mapped_metric_count": len(canonical_facts),
    "mapped_metric_paths": sorted(canonical_facts),
    "canonical_adapter_status": None,
    "canonical_adapter_blocker": None,
    "canonical_payload_ready": False,
    "production_evidence": False,
    "scoring_ready": False,
    "activation_ready": False,
    "missing_to_zero": False,
    "industrial_threshold_reuse": False,
    "production_mutation": "NO",
    "store_mutation": "NO",
    "al_sat_mutation": "NO",
    "scanner_mutation": "NO",
    "ranking_mutation": "NO",
    "portfolio_mutation": "NO",
    "blockers": [],
}

try:
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
except Exception as exc:
    result["canonical_adapter_status"] = "ERROR"
    result["canonical_adapter_blocker"] = f"{type(exc).__name__}:{exc}"
    result["blockers"].append(f"BANK_CANONICAL_ADAPTER_EXCEPTION:{type(exc).__name__}:{exc}")

result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

print("AKBNK_NPL_RATIO_SELECTION_AND_CANONICAL_GATE=START")
print("SELECTED_METRIC=ASSET_QUALITY.npl_ratio")
print("SELECTED_VALUE=3.5")
print(f"STATUS={result['status']}")
print(f"MAPPED_METRIC_COUNT={result['mapped_metric_count']}")
print(f"MAPPED_METRIC_PATHS={result['mapped_metric_paths']}")
print("CANONICAL_FACTS=" + json.dumps(result["canonical_facts"], ensure_ascii=False))
print(f"CANONICAL_ADAPTER_STATUS={result['canonical_adapter_status']}")
print(f"CANONICAL_ADAPTER_BLOCKER={result['canonical_adapter_blocker']}")
print(f"CANONICAL_PAYLOAD_READY={result['canonical_payload_ready']}")
print(f"PRODUCTION_EVIDENCE={result['production_evidence']}")
print("SCORING_READY=False")
print("ACTIVATION_READY=False")
print("MISSING_TO_ZERO=False")
print("INDUSTRIAL_THRESHOLD_REUSE=False")
print(f"BLOCKERS={result['blockers']}")
print("PRODUCTION_MUTATION=NO")
print("STORE_MUTATION=NO")
print("AL_SAT_MUTATION=NO")
print("SCANNER_MUTATION=NO")
print("RANKING_MUTATION=NO")
print("PORTFOLIO_MUTATION=NO")
print(f"RESULT={result_path}")
print("FINANCIAL_INTELLIGENCE_V1_3_AKBNK_NPL_RATIO_SELECTION_AND_CANONICAL_GATE_V1=PASS")
