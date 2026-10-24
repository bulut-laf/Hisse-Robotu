from backend.app.decision_support.risk_integration import (
    integrate_risk_layer,
)


def test_risk_layer_improves_quality():
    result = integrate_risk_layer(
        priority_score=75,
        risk_reward=2.5,
        volatility=2,
    )

    assert result["quality"] == "high"


def test_risk_layer_has_no_direct_trade_command():
    result = integrate_risk_layer(
        priority_score=50,
        risk_reward=1,
        volatility=5,
    )

    assert "buy" not in result
    assert "sell" not in result
    assert "signal" not in result
