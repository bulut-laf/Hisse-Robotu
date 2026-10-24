from backend.app.decision_engine.portfolio_decision_bridge import (
    evaluate_portfolio_position,
)


def test_portfolio_position_decision():
    result = evaluate_portfolio_position(
        {
            "symbol": "AKBNK",
            "trend": "positive",
            "risk": "controlled",
        }
    )

    assert result["symbol"] == "AKBNK"
    assert result["decision_label"] == "TUT"


def test_portfolio_position_no_trade_command():
    result = evaluate_portfolio_position({})

    assert "buy" not in str(result).lower()
    assert "sell" not in str(result).lower()
