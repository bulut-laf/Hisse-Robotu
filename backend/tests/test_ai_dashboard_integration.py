from backend.app.market_context.ai_dashboard_integration import (
    build_ai_dashboard_view,
)


def test_ai_dashboard_integration_flow():
    data = build_ai_dashboard_view(
        {
            "summary": "Temkinli pozitif",
            "positive_items": ["Global destek"],
            "risk_items": ["Fed"],
            "change_items": ["Risk azaldı"],
        }
    )

    assert data["component"] == "ai_market_context_card"
    assert data["payload"]["available"] is True
    assert data["payload"]["summary"] == "Temkinli pozitif"


def test_ai_dashboard_integration_has_no_trade_logic():
    data = build_ai_dashboard_view(None)

    assert data["payload"]["available"] is False
    assert "signal" not in data
    assert "technical_score" not in data
