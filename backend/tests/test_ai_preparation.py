from backend.app.market_context.ai_preparation import (
    AIEvaluationInput,
)


def test_ai_preparation_structure():
    data = AIEvaluationInput(
        date="2026-08-03",
        market_views=["BIST pozitif"],
        institution_views=["THYAO olumlu"],
        global_factors=["Fed"],
        fund_flows=["Teknoloji ETF"],
    ).to_dict()

    assert data["date"] == "2026-08-03"
    assert "BIST pozitif" in data["market_views"]
    assert "Fed" in data["global_factors"]


def test_ai_preparation_has_no_decision_fields():
    data = AIEvaluationInput(
        date="2026-08-03"
    ).to_dict()

    assert "signal" not in data
    assert "buy" not in data
    assert "technical_score" not in data
