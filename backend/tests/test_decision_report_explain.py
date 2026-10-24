from backend.app.decision_engine.decision_report_explain import (
    build_explainable_decision_report,
)


def test_explainable_report():
    result = build_explainable_decision_report(
        {
            "symbol": "AKBNK",
            "decision": "BUY_CANDIDATE",
            "sector": "strong",
            "technical": "positive",
            "risk": "controlled",
            "confidence": "high",
        }
    )

    assert result["symbol"] == "AKBNK"
    assert len(result["reasons"]) == 3


def test_explainable_report_has_no_direct_order():
    result = build_explainable_decision_report({})

    assert "buy" not in str(result)
    assert "sell" not in str(result)
