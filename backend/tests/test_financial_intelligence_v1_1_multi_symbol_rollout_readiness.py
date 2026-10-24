import json
from pathlib import Path

def test_multi_symbol_rollout_parser_does_not_fold_year_into_symbol():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FINANCIAL_INTELLIGENCE_V1_1_MULTI_SYMBOL_ROLLOUT_READINESS.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8-sig"))

    assert data["mode"] == "READ_ONLY_DISCOVERY"
    assert data["reference_symbol"] == "TUPRS"
    assert "YEAR_AND_PERIOD_MUST_NOT_BE_PART_OF_SYMBOL" in data["rules"]

    for c in data["candidates"]:
        assert not c["symbol"].endswith("_2026")
        assert "_" not in c["symbol"] or "." in c["symbol"]

    tuprs = [c for c in data["candidates"] if c["symbol"] == "TUPRS"]
    assert tuprs
    assert any(c["period"].startswith("2026_") for c in tuprs)
