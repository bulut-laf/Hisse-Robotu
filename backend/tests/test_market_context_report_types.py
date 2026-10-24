from backend.app.market_context.report_types import REPORT_TYPES


def test_recommendation_report_types_exist():
    assert "daily_recommendation" in REPORT_TYPES
    assert "weekly_recommendation" in REPORT_TYPES
    assert "model_portfolio" in REPORT_TYPES
    assert "target_price_report" in REPORT_TYPES


def test_market_commentary_types_are_preserved():
    assert "market_commentary" in REPORT_TYPES
    assert "kap_news" in REPORT_TYPES
