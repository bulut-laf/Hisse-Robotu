from backend.app.market_context.ai_summary_input import (
    AIPreparedSummary,
)


def test_ai_summary_input_structure():
    data = AIPreparedSummary(
        date="2026-08-03",
        market_points=["BIST pozitif"],
        positive_factors=["ABD vadeli pozitif"],
        risk_factors=["Fed belirsizliği"],
        institution_notes=["THYAO olumlu"],
    ).to_dict()

    assert data["date"] == "2026-08-03"
    assert "BIST pozitif" in data["market_points"]
    assert "Fed belirsizliği" in data["risk_factors"]


def test_ai_summary_does_not_make_decision():
    data = AIPreparedSummary(
        date="2026-08-03"
    ).to_dict()

    assert "signal" not in data
    assert "buy" not in data
    assert "technical_score" not in data
