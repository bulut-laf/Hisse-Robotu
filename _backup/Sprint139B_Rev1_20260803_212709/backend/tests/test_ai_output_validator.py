from backend.app.market_context.ai_output_validator import (
    validate_ai_output,
)


def test_ai_output_validator_accepts_safe_output():
    data = {
        "summary": "Temkinli pozitif",
        "positive_factors": ["Global destek"],
        "risk_factors": ["Faiz riski"],
        "conflicting_points": [],
    }

    assert validate_ai_output(data)


def test_ai_output_validator_rejects_trade_language():
    data = {
        "summary": "AL fırsatı",
        "positive_factors": [],
        "risk_factors": [],
        "conflicting_points": [],
    }

    assert not validate_ai_output(data)
