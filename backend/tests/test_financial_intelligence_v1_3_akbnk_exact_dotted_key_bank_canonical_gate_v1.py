import json
from pathlib import Path

def test_result():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend" / "data" / "financial_intelligence" / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_EXACT_DOTTED_KEY_BANK_CANONICAL_GATE.json"
    assert p.exists()
    d = json.loads(p.read_text(encoding="utf-8-sig"))
    assert d["canonical_facts"]["CAPITAL_ADEQUACY.capital_adequacy_ratio"] == "16.38"
    assert d["missing_to_zero"] is False
    assert d["industrial_threshold_reuse"] is False
