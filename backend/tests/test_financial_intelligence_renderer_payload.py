from pathlib import Path

from app.ui.financial_intelligence_renderer_payload import (
    build_financial_intelligence_renderer_payload,
)


def test_renderer_payload_default_tuprs():
    root = Path(__file__).resolve().parents[2]
    data = build_financial_intelligence_renderer_payload(root)

    assert data["status"] == "PASS"
    assert data["symbol"] == "TUPRS"
    assert "TUPRS" in data["eligible_symbols"]
    assert data["panel_artifact"].endswith("TUPRS_financial_intelligence_panel.json")
    assert data["mode"] == "READ_ONLY_RENDERER_PAYLOAD"


def test_renderer_payload_unknown_symbol_fails_closed():
    root = Path(__file__).resolve().parents[2]
    data = build_financial_intelligence_renderer_payload(root, symbol="ZZZZZ")

    assert data["status"] == "SYMBOL_NOT_ELIGIBLE"
    assert data["financial_health"] is None
    assert data["current_price"] is None
