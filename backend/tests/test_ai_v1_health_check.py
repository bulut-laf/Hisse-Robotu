from backend.app.market_context.ai_v1_health_check import (
    validate_ai_dashboard_payload,
)


def test_ai_v1_payload_is_valid():
    payload = {
        "available": True,
        "summary": "Temkinli pozitif",
        "positive_items": [],
        "risk_items": [],
        "change_items": [],
    }

    assert validate_ai_dashboard_payload(payload)


def test_ai_v1_health_has_no_trade_logic():
    payload = {
        "available": False,
    }

    assert not validate_ai_dashboard_payload(payload)
