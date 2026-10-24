import json
from pathlib import Path

def test_multi_symbol_rollout_readiness_is_read_only_contract():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FINANCIAL_INTELLIGENCE_V1_1_MULTI_SYMBOL_ROLLOUT_READINESS.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8-sig"))

    assert data["mode"] == "READ_ONLY_DISCOVERY"
    assert data["reference_symbol"] == "TUPRS"
    assert "NO_NEW_SCORE" in data["rules"]
    assert "NO_AL_SAT_MUTATION" in data["rules"]
    assert "NO_PORTFOLIO_MUTATION" in data["rules"]
    assert data["candidate_count"] >= 1
