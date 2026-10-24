from backend.app.market_context.report_types import (
    DEFAULT_REPORT_TYPE,
    is_valid_report_type,
)


def test_default_report_type_is_market_commentary():
    assert DEFAULT_REPORT_TYPE == "market_commentary"


def test_recommendation_types_are_valid():
    assert is_valid_report_type("daily_recommendation")
    assert is_valid_report_type("weekly_recommendation")


def test_unknown_report_type_is_invalid():
    assert not is_valid_report_type("unknown_type")
