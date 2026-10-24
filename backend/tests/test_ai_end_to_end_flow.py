from backend.app.market_context.ai_end_to_end_flow import (
    run_ai_evaluation_flow,
)


def test_ai_end_to_end_accepts_valid_output():
    data = run_ai_evaluation_flow(
        {
            "summary": "Temkinli pozitif",
            "positive_factors": ["Global destek"],
            "risk_factors": ["Faiz riski"],
            "conflicting_points": [],
        }
    )

    assert data["pipeline"] == "ai_evaluation_v1"
    assert data["result"]["valid"] is True


def test_ai_end_to_end_rejects_invalid_output():
    data = run_ai_evaluation_flow(
        {
            "summary": "AL fırsatı",
            "positive_factors": [],
            "risk_factors": [],
            "conflicting_points": [],
        }
    )

    assert data["result"]["valid"] is False
