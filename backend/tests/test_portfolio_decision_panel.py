from backend.app.portfolio.portfolio_decision_panel import (
    build_portfolio_decision_panel,
)


def test_portfolio_decision_panel():
    result = build_portfolio_decision_panel(
        [
            {
                "symbol": "AKBNK",
                "sector": "Bankacılık",
                "trend": "positive",
                "risk": "controlled",
                "decision": "TUT",
            }
        ]
    )

    assert result[0]["symbol"] == "AKBNK"
    assert result[0]["decision"] == "TUT"


def test_portfolio_decision_panel_empty():
    result = build_portfolio_decision_panel([])

    assert result == []
