from backend.app.decision_engine.analysis_connector import (
    connect_analysis_to_decision,
)


def test_analysis_connector():
    result = connect_analysis_to_decision(
        {
            "symbol": "AKBNK",
            "market": "positive",
            "sector": "strong",
            "technical": "positive",
            "risk": "controlled",
            "score": 85,
        }
    )

    assert result["symbol"] == "AKBNK"
    assert result["score"] == 85


def test_analysis_connector_no_trade_command():
    result = connect_analysis_to_decision({})

    assert "buy" not in str(result)
    assert "sell" not in str(result)
