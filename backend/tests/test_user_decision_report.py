from backend.app.decision_engine.user_decision_report import (
    build_user_decision_view,
)


def test_user_decision_view():
    result = build_user_decision_view(
        {
            "symbol": "AKBNK",
            "decision": "BUY_CANDIDATE",
            "score": 86,
            "sector": "Bankacılık",
            "technical": "positive",
            "risk": "controlled",
            "reasons": [
                "Güçlü sektör desteği"
            ],
        }
    )

    assert result["symbol"] == "AKBNK"
    assert result["score"] == 86
    assert len(result["reasons"]) == 1


def test_user_decision_view_no_trade_command():
    result = build_user_decision_view({})

    assert "buy" not in str(result)
    assert "sell" not in str(result)
