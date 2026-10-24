from backend.app.decision_engine.historical_decision_test import (
    evaluate_historical_results,
)


def test_historical_results():
    result = evaluate_historical_results(
        [
            {"outcome": "positive"},
            {"outcome": "negative"},
            {"outcome": "positive"},
        ]
    )

    assert result["total"] == 3
    assert result["successful"] == 2


def test_historical_results_no_trade_command():
    result = evaluate_historical_results([])

    assert "buy" not in str(result)
    assert "sell" not in str(result)
