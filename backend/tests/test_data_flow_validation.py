from backend.app.system.data_flow_validation import (
    validate_data_flow,
)


def test_data_flow_validation():
    result = validate_data_flow(
        {
            "source": True,
            "analysis": True,
            "decision": True,
            "dashboard": True,
            "report": True,
        }
    )

    assert result["ready"] is True


def test_data_flow_validation_missing():
    result = validate_data_flow({})

    assert result["ready"] is False
