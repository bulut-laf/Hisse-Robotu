from backend.app.sector_analysis.sector_strength import (
    calculate_sector_strength,
)


def test_sector_strength_classification():
    result = calculate_sector_strength(
        performance=6,
        volume_change=4,
    )

    assert result["status"] == "strong"


def test_sector_strength_has_no_trade_logic():
    result = calculate_sector_strength(
        performance=0,
    )

    assert "signal" not in result
    assert "buy" not in result
    assert "sell" not in result
