from pathlib import Path

from app.ui.financial_intelligence_ui_boundary import (
    build_financial_intelligence_ui_boundary,
)


def test_ui_boundary_tuprs():

    root = Path(__file__).resolve().parents[2]

    data = build_financial_intelligence_ui_boundary(root)

    assert data["status"] == "PASS"
    assert data["symbol"] == "TUPRS"
    assert data["panel_status"] == "PASS"

    cards = {
        row["key"]: row
        for row in data["metric_cards"]
    }

    assert cards["financial_health"]["value"] == "94/100"
    assert cards["cash_quality"]["value"] == "100/100"
    assert cards["capital_efficiency"]["value"] == "15/100"
    assert cards["risk"]["value"] == "Düşük"

    valuation = {
        row["key"]: row
        for row in data["valuation_rows"]
    }

    assert valuation["current_price"]["value"] == "385.00"
    assert valuation["attractive_entry_price"]["value"] == "179.71"
    assert valuation["valuation_status"]["value"] == "ok Pahalı"


def test_unknown_symbol_fails_closed():

    root = Path(__file__).resolve().parents[2]

    data = build_financial_intelligence_ui_boundary(
        root,
        symbol="ZZZZZ",
    )

    assert data["status"] == "SYMBOL_NOT_ELIGIBLE"
    assert data["metric_cards"] == []
    assert data["valuation_rows"] == []
