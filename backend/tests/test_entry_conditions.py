from backend.app.decision_engine.entry_conditions import (
    evaluate_entry_conditions,
)


def test_entry_conditions_candidate():
    result = evaluate_entry_conditions(
        {
            "market": "positive",
            "sector": "strong",
            "technical": "positive",
            "momentum": "positive",
            "risk": "controlled",
        }
    )

    assert result["entry_candidate"] is True
    assert result["passed_count"] == 5


def test_entry_conditions_no_direct_order():
    result = evaluate_entry_conditions({})

    assert "buy" not in str(result)
    assert "sell" not in str(result)
