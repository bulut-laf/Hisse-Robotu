from pathlib import Path

from app.analysis.financial_intelligence_selector_aware_panel import (
    build_selector_aware_financial_intelligence_panel,
)


def test_default_selector_aware_panel_resolves_tuprs():
    root = Path(__file__).resolve().parents[2]
    data = build_selector_aware_financial_intelligence_panel(root)

    assert data["status"] == "PASS"
    assert data["resolved_symbol"] == "TUPRS"
    assert "TUPRS" in data["eligible_symbols"]
    assert data["panel"] is not None
    assert data["panel_artifact"].endswith("TUPRS_financial_intelligence_panel.json")
    assert data["mode"] == "READ_ONLY_PANEL_ADAPTER"


def test_explicit_tuprs_resolves():
    root = Path(__file__).resolve().parents[2]
    data = build_selector_aware_financial_intelligence_panel(root, symbol="tuprs")

    assert data["status"] == "PASS"
    assert data["requested_symbol"] == "TUPRS"
    assert data["resolved_symbol"] == "TUPRS"


def test_unknown_symbol_fails_closed():
    root = Path(__file__).resolve().parents[2]
    data = build_selector_aware_financial_intelligence_panel(root, symbol="ZZZZZ")

    assert data["status"] == "SYMBOL_NOT_ELIGIBLE"
    assert data["panel"] is None
