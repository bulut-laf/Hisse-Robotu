from backend.app.market_context.ai_evaluation_service import (
    create_evaluation_record,
)


def test_ai_evaluation_service_creates_archive_record():
    data = create_evaluation_record(
        date="2026-08-03",
        package_id="daily-001",
        output={"summary": "Temkinli pozitif"},
    )

    assert data["input_package_id"] == "daily-001"
    assert data["report_count"] == 1
    assert data["reports"][0]["summary"] == "Temkinli pozitif"


def test_service_has_no_trade_decision():
    data = create_evaluation_record(
        date="2026-08-03",
        package_id="daily-001",
        output={},
    )

    assert "signal" not in data
    assert "technical_score" not in data
