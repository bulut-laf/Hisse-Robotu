from pathlib import Path

from app.ui.financial_intelligence_renderer_payload import (
    build_financial_intelligence_renderer_payload,
)


def test_renderer_payload_real_tuprs_source_aware_values():
    root = Path(__file__).resolve().parents[2]
    data = build_financial_intelligence_renderer_payload(root)

    assert data["status"] == "PASS"
    assert data["symbol"] == "TUPRS"
    assert data["panel_status"] == "PASS"

    assert float(data["financial_health"]) == 94.0
    assert float(data["cash_quality"]) == 100.0
    assert float(data["capital_efficiency"]) == 15.0
    assert str(data["risk"]).upper() == "LOW"
    assert float(data["current_price"]) == 385.0
    assert abs(float(data["attractive_entry_price"]) - 179.71146) < 0.02
    assert str(data["valuation_status"]).upper().startswith("VERY_EXPENS")

    assert data["acceptance_artifact"] is not None
    assert data["mode"] == "READ_ONLY_RENDERER_PAYLOAD"


def test_renderer_payload_unknown_symbol_fails_closed():
    root = Path(__file__).resolve().parents[2]
    data = build_financial_intelligence_renderer_payload(root, symbol="ZZZZZ")
    assert data["status"] == "SYMBOL_NOT_ELIGIBLE"
