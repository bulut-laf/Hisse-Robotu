from backend.app.decision_engine.exit_conditions import (
    evaluate_exit_conditions,
)


def test_exit_conditions_candidate():
    result = evaluate_exit_conditions(
        {
            "trend": "broken",
            "momentum": "negative",
            "risk": "high",
            "market": "negative",
        }
    )

    assert result["exit_candidate"] is True
    assert result["exit_score"] == 4


def test_exit_conditions_no_direct_order():
    result = evaluate_exit_conditions({})

    assert "buy" not in str(result)
    assert "sell" not in str(result)
