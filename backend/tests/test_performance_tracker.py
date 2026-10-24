from backend.app.decision_engine.performance_tracker import (
    calculate_decision_performance,
)


def test_performance_tracker():
    result = calculate_decision_performance(
        [
            {"result": "positive"},
            {"result": "negative"},
            {"result": "positive"},
        ]
    )

    assert result["total_decisions"] == 3
    assert result["successful_decisions"] == 2


def test_performance_tracker_no_trade_command():
    result = calculate_decision_performance([])

    assert "buy" not in str(result).lower()
    assert "sell" not in str(result).lower()
