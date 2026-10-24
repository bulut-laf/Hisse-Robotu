from backend.app.decision_engine.system_validation import (
    validate_decision_system,
)


def test_system_validation_ready():
    result = validate_decision_system(
        {
            "scan": True,
            "decision": True,
            "report": True,
            "performance": True,
        }
    )

    assert result["ready"] is True


def test_system_validation_no_trade_command():
    result = validate_decision_system({})

    assert "buy" not in str(result).lower()
    assert "sell" not in str(result).lower()
