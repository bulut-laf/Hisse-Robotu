from backend.app.market_context.ai_evaluation_archive import (
    AIEvaluationArchiveRecord,
)


def test_ai_evaluation_archive_record():
    data = AIEvaluationArchiveRecord(
        date="2026-08-03",
        summary="Temkinli pozitif",
        risk_factors=["Faiz riski"],
        positive_factors=["Global destek"],
    ).to_dict()

    assert data["summary"] == "Temkinli pozitif"
    assert "Faiz riski" in data["risk_factors"]


def test_ai_archive_has_no_trade_logic():
    data = AIEvaluationArchiveRecord(
        date="2026-08-03",
        summary="Test",
    ).to_dict()

    assert "signal" not in data
    assert "technical_score" not in data
