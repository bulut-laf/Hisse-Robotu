from backend.app.market_context.ai_history import (
    AIEvaluationHistory,
)


def test_ai_history_stores_multiple_days():
    history = AIEvaluationHistory()

    history.add(
        {
            "date": "2026-08-03",
            "summary": "Temkinli pozitif",
        }
    )

    history.add(
        {
            "date": "2026-08-04",
            "summary": "Pozitif",
        }
    )

    data = history.to_dict()

    assert data["evaluation_count"] == 2
    assert data["evaluations"][1]["summary"] == "Pozitif"


def test_ai_history_has_no_trade_logic():
    data = AIEvaluationHistory().to_dict()

    assert "signal" not in data
    assert "technical_score" not in data
