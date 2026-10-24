from backend.app.decision_support.decision_report import (
    build_decision_report,
)


def test_decision_report_creation():
    result = build_decision_report(
        {
            "symbol": "AKBNK",
            "priority": "high",
            "score": 90,
            "sector": "Bankacılık",
            "risk": "controlled",
        }
    )

    assert result["symbol"] == "AKBNK"
    assert result["sector"] == "Bankacılık"


def test_decision_report_has_no_trade_command():
    result = build_decision_report({})

    assert "buy" not in str(result)
    assert "sell" not in str(result)
