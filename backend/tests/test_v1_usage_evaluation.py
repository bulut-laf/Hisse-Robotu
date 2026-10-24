from backend.app.system.v1_usage_evaluation import (
    evaluate_v1_usage,
)


def test_v1_usage_evaluation():
    result = evaluate_v1_usage(
        {
            "technical": True,
            "usability": True,
            "explainability": True,
            "stability": True,
        }
    )

    assert result["ready"] is True


def test_v1_usage_evaluation_missing():
    result = evaluate_v1_usage({})

    assert result["ready"] is False
