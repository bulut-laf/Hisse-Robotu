from backend.app.market_context.report_type_integration import (
    prepare_document_metadata,
)


def test_report_type_integration_dependency_exists():
    data = prepare_document_metadata(
        source="ABC",
        document_date="2026-08-03",
        input_type="pdf",
        report_type="weekly_recommendation",
    )

    assert data["report_type"] == "weekly_recommendation"
