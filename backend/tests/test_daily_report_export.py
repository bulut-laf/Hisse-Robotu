from backend.app.reporting.daily_report_export import (
    export_daily_report_data,
)


def test_daily_report_export():
    result = export_daily_report_data(
        {
            "date": "2026-08-03",
            "market": "positive",
            "sectors": ["Bankacılık"],
            "candidates": ["AKBNK"],
            "positions": ["THYAO"],
        }
    )

    assert result["date"] == "2026-08-03"
    assert result["candidates"] == ["AKBNK"]


def test_daily_report_export_empty():
    result = export_daily_report_data({})

    assert result["candidates"] == []
