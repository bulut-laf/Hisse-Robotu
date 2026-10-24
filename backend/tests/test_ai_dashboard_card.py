from backend.app.market_context.ai_dashboard_card import AIDashboardCard


def test_ai_dashboard_card_structure():
    data = AIDashboardCard(
        summary="Temkinli pozitif",
        positive_items=["Global destek"],
        risk_items=["Fed belirsizliği"],
        change_items=["Risk azaldı"],
    ).to_dict()

    assert data["title"] == "AI Piyasa Değerlendirmesi"
    assert "Global destek" in data["positive_items"]


def test_ai_dashboard_card_has_no_trade_logic():
    data = AIDashboardCard().to_dict()

    assert "signal" not in data
    assert "technical_score" not in data
