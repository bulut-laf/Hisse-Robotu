from backend.app.market_context.ai_comparison import (
    AIComparisonResult,
)


def test_ai_comparison_structure():
    data = AIComparisonResult(
        previous_date="2026-08-03",
        current_date="2026-08-04",
        changed_items=["Görünüm pozitife döndü"],
        increased_risks=["Faiz riski"],
        reduced_risks=["Global belirsizlik"],
    ).to_dict()

    assert data["previous_date"] == "2026-08-03"
    assert "Görünüm pozitife döndü" in data["changed_items"]


def test_ai_comparison_has_no_trade_logic():
    data = AIComparisonResult(
        previous_date="2026-08-03",
        current_date="2026-08-04",
    ).to_dict()

    assert "signal" not in data
    assert "technical_score" not in data
