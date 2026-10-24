import json
from pathlib import Path

def test_akbnk_tier1_selection_and_canonical_gate():
    root = Path(__file__).resolve().parents[2]
    path = root / "backend" / "data" / "financial_intelligence" / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_TIER1_SELECTION_AND_CANONICAL_GATE.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    assert data["selected_metric"] == "CAPITAL_ADEQUACY.tier1_capital_ratio"
    assert data["selected_value"] == "13.33"
    assert data["canonical_facts"]["CAPITAL_ADEQUACY.tier1_capital_ratio"] == "13.33"
    assert data["canonical_facts"]["CAPITAL_ADEQUACY.capital_adequacy_ratio"] == "16.38"
    assert data["evidence_hit_count"] >= 1
    assert data["missing_to_zero"] is False
    assert data["industrial_threshold_reuse"] is False
    assert data["scoring_ready"] is False
    assert data["activation_ready"] is False
    assert data["production_mutation"] == "NO"
    assert data["store_mutation"] == "NO"
    assert data["al_sat_mutation"] == "NO"
    assert data["scanner_mutation"] == "NO"
    assert data["ranking_mutation"] == "NO"
    assert data["portfolio_mutation"] == "NO"
