import json
from pathlib import Path


def test_multi_symbol_registry_contract():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FINANCIAL_INTELLIGENCE_V1_1_MULTI_SYMBOL_REGISTRY.json"
    assert p.exists()

    data = json.loads(p.read_text(encoding="utf-8-sig"))

    assert data["status"] == "PASS"
    assert data["mode"] == "READ_ONLY_REGISTRY"
    assert data["symbol_count"] >= 1
    assert "TUPRS" in [x["symbol"] for x in data["symbols"]]
    assert "REGISTRY_IS_READ_ONLY" in data["rules"]
    assert "NO_SYNTHETIC_SYMBOLS" in data["rules"]
    assert "NO_AL_SAT_SCANNER_RANKING_PORTFOLIO_MUTATION" in data["rules"]


def test_tuprs_registry_entry_is_present_and_unique():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FINANCIAL_INTELLIGENCE_V1_1_MULTI_SYMBOL_REGISTRY.json"
    data = json.loads(p.read_text(encoding="utf-8-sig"))

    rows = [x for x in data["symbols"] if x["symbol"] == "TUPRS"]
    assert len(rows) == 1
    assert rows[0]["panel_artifact"].endswith("TUPRS_financial_intelligence_panel.json")
