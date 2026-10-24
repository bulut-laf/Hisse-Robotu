from backend.app.market_context.recommendation_archive import (
    RecommendationArchiveData,
)


def test_weekly_recommendation_archive_format():
    item = RecommendationArchiveData(
        report_type="weekly_recommendation",
        buy=["THYAO"],
        watch=["EREGL"],
        target_prices={"THYAO": "350"},
        time_horizon="weekly",
    )

    data = item.to_dict()

    assert data["report_type"] == "weekly_recommendation"
    assert data["recommendations"]["buy"] == ["THYAO"]
    assert data["target_prices"]["THYAO"] == "350"


def test_archive_data_has_no_trading_decision_field():
    item = RecommendationArchiveData(
        report_type="daily_recommendation"
    )

    assert "signal" not in item.to_dict()
    assert "technical_score" not in item.to_dict()
