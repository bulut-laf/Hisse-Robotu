from backend.app.market_context.ai_history_view import (
    build_ai_history_view,
)


def test_ai_history_view_builds_rows():
    data = build_ai_history_view(
        [
            {
                "date": "2026-08-03",
                "summary": "Temkinli pozitif",
                "risk_factors": ["Faiz"],
                "positive_factors": ["Global destek"],
            }
        ]
    )

    assert data[0]["summary"] == "Temkinli pozitif"
    assert "Faiz" in data[0]["risk_factors"]


def test_ai_history_view_has_no_trade_logic():
    data = build_ai_history_view([])

    assert isinstance(data, list)
    assert "signal" not in str(data)
    assert "technical_score" not in str(data)
