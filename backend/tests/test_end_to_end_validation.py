from backend.app.system.end_to_end_validation import (
    validate_end_to_end_flow,
)


def test_end_to_end_flow():
    result = validate_end_to_end_flow(
        {
            "data": True,
            "analysis": True,
            "sector": True,
            "risk": True,
            "decision": True,
            "dashboard": True,
            "report": True,
        }
    )

    assert result["ready"] is True


def test_end_to_end_flow_missing():
    result = validate_end_to_end_flow({})

    assert result["ready"] is False
