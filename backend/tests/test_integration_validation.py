from backend.app.system.integration_validation import (
    validate_system_integration,
)


def test_integration_validation():
    result = validate_system_integration(
        {
            "decision_engine": True,
            "sector_analysis": True,
            "portfolio": True,
            "reporting": True,
        }
    )

    assert result["ready"] is True


def test_integration_validation_empty():
    result = validate_system_integration({})

    assert result["ready"] is False
