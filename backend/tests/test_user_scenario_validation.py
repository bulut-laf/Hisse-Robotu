from backend.app.system.user_scenario_validation import (
    validate_user_scenarios,
)


def test_user_scenario_validation():
    result = validate_user_scenarios(
        {
            "daily_analysis": True,
            "candidate_review": True,
            "portfolio_check": True,
            "report_access": True,
        }
    )

    assert result["ready"] is True


def test_user_scenario_validation_missing():
    result = validate_user_scenarios({})

    assert result["ready"] is False
