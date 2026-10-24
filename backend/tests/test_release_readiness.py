from backend.app.system.release_readiness import (
    validate_release_readiness,
)


def test_release_readiness():
    result = validate_release_readiness(
        {
            "modules": True,
            "data_flow": True,
            "dashboard": True,
            "performance": True,
            "user_flow": True,
        }
    )

    assert result["ready"] is True


def test_release_readiness_missing():
    result = validate_release_readiness({})

    assert result["ready"] is False
