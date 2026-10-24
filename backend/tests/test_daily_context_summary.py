from backend.app.market_context.daily_context_summary import (
    DailyContextSummary,
)


def test_daily_context_collects_multiple_sources():
    summary = DailyContextSummary(date="2026-08-03")

    summary.add_document(
        {
            "source": "ICBC",
            "report_type": "market_commentary",
        }
    )

    summary.add_document(
        {
            "source": "Global Report",
            "report_type": "global_market_commentary",
        }
    )

    data = summary.to_dict()

    assert data["document_count"] == 2
    assert len(data["documents"]) == 2


def test_daily_context_has_no_trading_logic():
    data = DailyContextSummary(
        date="2026-08-03"
    ).to_dict()

    assert "signal" not in data
    assert "technical_score" not in data
