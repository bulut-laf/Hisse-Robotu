from backend.app.system.signal_quality_validation import (
    validate_signal_quality,
)


def test_signal_quality_validation():
    result = validate_signal_quality(
        {
            "decision": "AL ADAYI",
            "score": 82,
            "risk": "Orta",
            "reason": "Sektör güçlü",
        }
    )

    assert result["ready"] is True


def test_signal_quality_validation_missing():
    result = validate_signal_quality({})

    assert result["ready"] is False
