from backend.app.market_context.global_market_context import GlobalMarketContext


def test_global_context_structure():
    data = GlobalMarketContext(
        us_market="Pozitif",
        asia_market="Karışık",
        macro_topics=["Fed"],
        commodities=["Petrol"],
    ).to_dict()

    assert data["report_type"] == "global_market_commentary"
    assert data["regions"]["us_market"] == "Pozitif"
    assert "Fed" in data["macro_topics"]


def test_global_context_is_not_trading_signal():
    data = GlobalMarketContext().to_dict()
    assert "signal" not in data
    assert "technical_score" not in data
