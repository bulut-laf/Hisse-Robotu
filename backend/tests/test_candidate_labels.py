from backend.app.decision_engine.candidate_labels import (
    add_decision_labels,
)


def test_candidate_labels():
    result = add_decision_labels(
        [
            {
                "symbol": "AKBNK",
                "decision_label": "AL ADAYI",
            }
        ]
    )

    assert result[0]["symbol"] == "AKBNK"
    assert result[0]["decision_available"] is True
    assert result[0]["decision_label"] == "AL ADAYI"


def test_candidate_labels_no_trade_command():
    result = add_decision_labels([])

    assert "buy" not in str(result).lower()
    assert "sell" not in str(result).lower()
