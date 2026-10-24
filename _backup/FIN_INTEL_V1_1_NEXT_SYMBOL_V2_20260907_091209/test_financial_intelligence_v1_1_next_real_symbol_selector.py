import json
from pathlib import Path

def test_next_symbol_selector_is_read_only_and_never_reselects_tuprs():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FINANCIAL_INTELLIGENCE_V1_1_NEXT_REAL_SYMBOL_SELECTION.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    assert data["mode"] == "READ_ONLY_SELECTION"
    assert data["reference_symbol"] == "TUPRS"
    assert data["selected_symbol"] != "TUPRS"
    assert "NO_ARBITRARY_SYMBOL_SELECTION" in data["rules"]
    assert "NO_AL_SAT_SCANNER_RANKING_PORTFOLIO_MUTATION" in data["rules"]
