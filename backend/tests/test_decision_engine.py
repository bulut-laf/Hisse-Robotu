from backend.app.decision_support.decision_engine import (
    evaluate_decision_context,
)


def test_decision_engine_candidate():
    result = evaluate_decision_context(
        "positive",
        "strong",
        "positive",
        "controlled",
    )

    assert result["decision"] == "candidate"


def test_decision_engine_has_no_direct_order():
    result = evaluate_decision_context(
        "neutral",
        "weak",
        "negative",
        "high",
    )

    assert "buy" not in str(result)
    assert "sell" not in str(result)
