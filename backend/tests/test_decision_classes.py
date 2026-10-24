from backend.app.decision_engine.decision_classes import (
    classify_decision,
)


def test_decision_classes():
    assert classify_decision(85) == "BUY_CANDIDATE"
    assert classify_decision(65) == "HOLD"
    assert classify_decision(20) == "SELL_CANDIDATE"


def test_decision_classes_no_direct_order():
    result = classify_decision(50)

    assert result == "WATCH"
    assert "buy" not in result.lower()
    assert "sell" not in result.lower()
