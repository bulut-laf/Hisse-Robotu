from backend.app.sector_analysis.sector_membership import (
    map_sector_members,
)


def test_sector_membership_mapping():
    result = map_sector_members(
        {
            "name": "Bankacılık",
            "status": "strong",
        },
        ["AKBNK", "GARAN"],
    )

    assert result["sector"] == "Bankacılık"
    assert result["symbol_count"] == 2
    assert "AKBNK" in result["symbols"]


def test_sector_membership_has_no_trade_logic():
    result = map_sector_members(
        {"name": "Sanayi"},
        [],
    )

    assert "signal" not in result
    assert "buy" not in result
    assert "sell" not in result
