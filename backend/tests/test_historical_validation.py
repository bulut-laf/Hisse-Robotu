from backend.app.decision_engine.historical_validation import (
    validate_historical_decision,
)


def test_historical_validation():
    result = validate_historical_decision(
        [
            {"result": "positive"},
            {"result": "negative"},
            {"result": "positive"},
        ]
    )

    assert result["total"] == 3
    assert result["positive"] == 2


def test_validation_has_no_trade_command():
    result = validate_historical_decision([])

    assert "buy" not in str(result)
    assert "sell" not in str(result)
