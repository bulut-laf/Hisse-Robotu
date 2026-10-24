from pathlib import Path

from app.ui.financial_intelligence_renderer_contract import (
    build_financial_intelligence_renderer_contract,
)


def test_renderer_contract_default_tuprs():
    root = Path(__file__).resolve().parents[2]
    data = build_financial_intelligence_renderer_contract(root)

    assert data["status"] == "PASS"
    assert data["symbol"] == "TUPRS"
    assert "TUPRS" in data["eligible_symbols"]
    assert data["panel"] is not None
    assert data["panel_artifact"].endswith("TUPRS_financial_intelligence_panel.json")
    assert data["mode"] == "READ_ONLY_RENDERER_CONTRACT"


def test_renderer_contract_unknown_symbol_fails_closed():
    root = Path(__file__).resolve().parents[2]
    data = build_financial_intelligence_renderer_contract(root, symbol="ZZZZZ")

    assert data["status"] == "SYMBOL_NOT_ELIGIBLE"
    assert data["panel"] is None
