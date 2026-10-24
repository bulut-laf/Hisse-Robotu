from backend.app.decision_engine.dashboard_decision_card import (
    build_decision_card,
)


def test_dashboard_decision_card():
    result = build_decision_card(
        {
            "symbol": "AKBNK",
            "decision_label": "AL ADAYI",
            "score": 86,
            "sector": "Bankacılık",
            "risk": "controlled",
            "reasons": ["Güçlü sektör"],
        }
    )

    assert result["symbol"] == "AKBNK"
    assert result["status"] == "AL ADAYI"
    assert result["score"] == 86


def test_dashboard_card_no_trade_command():
    result = build_decision_card({})

    assert "buy" not in str(result).lower()
    assert "sell" not in str(result).lower()
