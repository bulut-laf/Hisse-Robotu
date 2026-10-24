from backend.app.system.decision_review_validation import (
    validate_decision_review,
)


def test_decision_review_validation():
    result = validate_decision_review(
        {
            "decision": "AL ADAYI",
            "score": 84,
            "reasons": ["Sektör güçlü", "Trend olumlu"],
            "risk": "Orta",
        }
    )

    assert result["ready"] is True


def test_decision_review_validation_missing():
    result = validate_decision_review({})

    assert result["ready"] is False
