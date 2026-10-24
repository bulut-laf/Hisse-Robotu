from backend.app.decision_engine.decision_display import (
    format_decision_display,
)


def test_decision_display():
    result = format_decision_display(
        {
            "symbol": "AKBNK",
            "decision": "BUY_CANDIDATE",
            "score": 86,
            "reasons": ["Güçlü sektör"],
        }
    )

    assert result["display_status"] == "AL ADAYI"
    assert result["symbol"] == "AKBNK"


def test_decision_display_no_direct_command():
    result = format_decision_display({})

    assert "buy" not in str(result).lower()
    assert "sell" not in str(result).lower()
