from backend.app.sector_analysis.sector_report import (
    build_sector_report,
)


def test_sector_report_returns_top_sectors():
    result = build_sector_report(
        [
            {"name": "Bankacılık", "score": 8},
            {"name": "Sanayi", "score": 3},
            {"name": "Gıda", "score": 1},
            {"name": "Turizm", "score": -2},
        ]
    )

    assert result["sector_count"] == 4
    assert result["top_sectors"][0]["name"] == "Bankacılık"


def test_sector_report_has_no_trade_logic():
    result = build_sector_report([])

    assert "signal" not in result
    assert "buy" not in str(result)
    assert "sell" not in str(result)
