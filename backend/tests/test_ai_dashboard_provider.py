from backend.app.market_context.ai_dashboard_provider import (
    build_ai_dashboard_payload,
)


def test_ai_dashboard_provider_builds_payload():
    data = build_ai_dashboard_payload(
        {
            "summary": "Temkinli pozitif",
            "positive_items": ["Global destek"],
            "risk_items": ["Fed"],
            "change_items": ["Risk azaldı"],
        }
    )

    assert data["available"] is True
    assert data["summary"] == "Temkinli pozitif"
    assert "Fed" in data["risk_items"]


def test_ai_dashboard_provider_has_no_trade_logic():
    data = build_ai_dashboard_payload(None)

    assert data["available"] is False
    assert "signal" not in data
    assert "technical_score" not in data
