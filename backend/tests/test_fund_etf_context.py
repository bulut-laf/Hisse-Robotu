from backend.app.market_context.fund_etf_context import FundEtfContext


def test_fund_etf_context_structure():
    data = FundEtfContext(
        equity_etfs=["S&P500 ETF"],
        sector_etfs=["Technology ETF"],
        commodity_funds=["Gold ETF"],
    ).to_dict()

    assert data["report_type"] == "fund_etf_commentary"
    assert "S&P500 ETF" in data["equity_etfs"]
    assert "Gold ETF" in data["commodity_funds"]


def test_fund_etf_context_has_no_trade_signal():
    data = FundEtfContext().to_dict()

    assert "signal" not in data
    assert "technical_score" not in data
