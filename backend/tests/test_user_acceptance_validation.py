from backend.app.system.user_acceptance_validation import (
    run_user_acceptance_validation,
)


def test_user_acceptance_validation():
    result = run_user_acceptance_validation(
        {
            "dashboard": True,
            "ranking": True,
            "sector": True,
            "portfolio": True,
            "report": True,
        }
    )

    assert result["accepted"] is True


def test_user_acceptance_validation_empty():
    result = run_user_acceptance_validation({})

    assert result["accepted"] is False
