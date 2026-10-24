import json
from pathlib import Path

FORBIDDEN = {"ADAPTER", "BUSINESS", "QUALITY", "COVERAGE", "MARKET", "TERM", "MAP", "SERIES", "EVIDENCE", "MANIFEST"}

def test_next_real_symbol_selector_v2_uses_exact_symbol_sources_only():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FINANCIAL_INTELLIGENCE_V1_1_NEXT_REAL_SYMBOL_SELECTION.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8-sig"))

    assert data["mode"] == "READ_ONLY_EXACT_SYMBOL_SELECTION"
    assert data["reference_symbol"] == "TUPRS"
    assert "NO_FILENAME_TOKEN_SYMBOL_HEURISTICS" in data["rules"]
    assert data["selected_symbol"] not in FORBIDDEN

    for c in data["top_candidates"]:
        assert c["symbol"] not in FORBIDDEN

    if data["selected_symbol"] is not None:
        assert data["selected_acceptance_file_count"] >= 1
