from backend.app.decision_engine.score_weights import (
    calculate_weighted_score,
)


def test_weighted_score_calculation():
    result = calculate_weighted_score(
        {
            "market": 90,
            "sector": 80,
            "technical": 90,
            "momentum": 70,
            "risk": 80,
        }
    )

    assert result["score"] > 80
    assert "technical" in result["weights"]


def test_weighted_score_has_no_trade_command():
    result = calculate_weighted_score({})

    assert "buy" not in str(result)
    assert "sell" not in str(result)
