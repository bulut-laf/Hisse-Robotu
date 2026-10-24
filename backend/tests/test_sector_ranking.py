from backend.app.sector_analysis.sector_ranking import (
    rank_sectors,
)


def test_sector_ranking_orders_by_score():
    result = rank_sectors(
        [
            {"name": "Sanayi", "score": 2},
            {"name": "Bankacılık", "score": 8},
            {"name": "Gıda", "score": -1},
        ]
    )

    assert result[0]["name"] == "Bankacılık"
    assert result[-1]["name"] == "Gıda"


def test_sector_ranking_has_no_trade_logic():
    result = rank_sectors([])

    assert isinstance(result, list)
    assert "signal" not in str(result)
