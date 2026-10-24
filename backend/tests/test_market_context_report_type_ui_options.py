from backend.app.market_context.report_type_ui_options import (
    REPORT_TYPE_LABELS,
    get_report_type_options,
)


def test_ui_contains_recommendation_report_types():
    options = get_report_type_options()

    assert "daily_recommendation" in options
    assert "weekly_recommendation" in options
    assert "model_portfolio" in options


def test_ui_labels_are_separate_from_trading_logic():
    assert "Günlük AL-SAT Önerisi" == REPORT_TYPE_LABELS["daily_recommendation"]
    assert "signal" not in REPORT_TYPE_LABELS
    assert "technical_score" not in REPORT_TYPE_LABELS
