from pathlib import Path

from app.ui.financial_intelligence_presentation_contract import (
    build_financial_intelligence_presentation_contract,
)


def test_presentation_contract_tuprs():

    root = Path(__file__).resolve().parents[2]

    data = (
        build_financial_intelligence_presentation_contract(
            root
        )
    )

    assert data["status"] == "PASS"
    assert data["symbol"] == "TUPRS"

    cards = {
        row["key"]: row
        for row in data["cards"]
    }

    assert (
        cards["financial_health"]["display_value"]
        == "94/100"
    )

    assert (
        cards["cash_quality"]["display_value"]
        == "100/100"
    )

    assert (
        cards["capital_efficiency"]["display_value"]
        == "15/100"
    )

    assert (
        cards["risk"]["display_value"]
        == "Düşük"
    )

    valuation = data["valuation"]

    assert (
        valuation["current_price"]["display_value"]
        == "385.00"
    )

    assert (
        valuation[
            "attractive_entry_price"
        ]["display_value"]
        == "179.71"
    )

    assert (
        valuation[
            "valuation_status"
        ]["display_value"]
        == "ok Pahalı"
    )


def test_unknown_symbol_fails_closed():

    root = Path(__file__).resolve().parents[2]

    data = (
        build_financial_intelligence_presentation_contract(
            root,
            symbol="ZZZZZ",
        )
    )

    assert (
        data["status"]
        == "SYMBOL_NOT_ELIGIBLE"
    )

    assert data["cards"] == []
