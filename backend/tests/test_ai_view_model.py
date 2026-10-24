from backend.app.market_context.ai_view_model import (
    AIViewModel,
)


def test_ai_view_model_structure():
    data = AIViewModel(
        summary="Temkinli pozitif",
        positive_factors=["Global destek"],
        risk_factors=["Faiz riski"],
        changed_items=["Görünüm iyileşti"],
        watch_items=["Fed"],
    ).to_dict()

    assert data["summary"] == "Temkinli pozitif"
    assert "Fed" in data["watch_items"]


def test_ai_view_model_has_no_trade_logic():
    data = AIViewModel().to_dict()

    assert "signal" not in data
    assert "technical_score" not in data
