from backend.app.market_context.report_type_integration import (
    prepare_document_metadata,
)


def test_selected_report_type_is_added_to_metadata():
    data = prepare_document_metadata(
        source="ABC Yatırım",
        document_date="2026-08-03",
        input_type="pdf",
        report_type="weekly_recommendation",
    )

    assert data["report_type"] == "weekly_recommendation"
    assert data["source"] == "ABC Yatırım"


def test_metadata_does_not_create_trading_decision():
    data = prepare_document_metadata(
        source="ICBC",
        document_date="2026-08-03",
        input_type="text",
        report_type="market_commentary",
    )

    assert "signal" not in data
    assert "technical_score" not in data
