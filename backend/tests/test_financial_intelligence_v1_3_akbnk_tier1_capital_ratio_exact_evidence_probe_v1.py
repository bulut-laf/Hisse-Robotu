import json
from pathlib import Path

def test_tier1_probe_result():
    root = Path(__file__).resolve().parents[2]
    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_TIER1_CAPITAL_RATIO_EXACT_EVIDENCE_PROBE.json"
    )
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    assert data["target_metric"] == "CAPITAL_ADEQUACY.tier1_capital_ratio"
    assert data["metric_value_selected"] is None
    assert data["selection_ready"] is False
    assert data["missing_to_zero"] is False
    assert data["production_mutation"] == "NO"
    assert data["store_mutation"] == "NO"
    assert data["al_sat_mutation"] == "NO"
