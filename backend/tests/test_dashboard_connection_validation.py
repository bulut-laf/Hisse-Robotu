from backend.app.system.dashboard_connection_validation import (
    validate_dashboard_connection,
)


def test_dashboard_connection_validation():
    result = validate_dashboard_connection(
        {
            "decision_card": True,
            "ranking": True,
            "sector": True,
            "portfolio": True,
            "report": True,
        }
    )

    assert result["ready"] is True


def test_dashboard_connection_validation_missing():
    result = validate_dashboard_connection({})

    assert result["ready"] is False
