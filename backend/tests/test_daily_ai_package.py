from backend.app.market_context.daily_ai_package import DailyAIPackage


def test_daily_ai_package_combines_contexts():
    data = DailyAIPackage(
        date="2026-08-03",
        market_context=["BIST pozitif"],
        global_context=["ABD vadeli pozitif"],
        institution_context=["Kurum görüşü olumlu"],
        fund_etf_context=["Teknoloji ETF güçlü"],
        risks=["Fed belirsizliği"],
    ).to_dict()

    assert data["date"] == "2026-08-03"
    assert "BIST pozitif" in data["market_context"]
    assert "Fed belirsizliği" in data["risks"]


def test_daily_ai_package_has_no_trading_decision():
    data = DailyAIPackage(date="2026-08-03").to_dict()

    assert "signal" not in data
    assert "buy" not in data
    assert "technical_score" not in data
