import json
from pathlib import Path

def test_akbnk_npl_ratio_exact_evidence_probe():
    root = Path(__file__).resolve().parents[2]
    path = root / "backend" / "data" / "financial_intelligence" / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_NPL_RATIO_EXACT_EVIDENCE_PROBE.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    assert data["status"] == "PASS"
    assert data["target_metric"] == "ASSET_QUALITY.npl_ratio"
    assert data["metric_value_selected"] is None
    assert data["selection_ready"] is False
    assert data["canonical_production_ready"] is False
    assert data["scoring_ready"] is False
    assert data["activation_ready"] is False
    assert data["missing_to_zero"] is False
    assert data["industrial_threshold_reuse"] is False
    assert data["production_mutation"] == "NO"
    assert data["store_mutation"] == "NO"
    assert data["al_sat_mutation"] == "NO"
    assert data["scanner_mutation"] == "NO"
    assert data["ranking_mutation"] == "NO"
    assert data["portfolio_mutation"] == "NO"
