from backend.app.decision_support.sector_stock_priority import (
    calculate_sector_stock_priority,
)


def test_sector_stock_priority():
    result = calculate_sector_stock_priority(
        sector_score=80,
        technical_score=85,
    )

    assert result["priority"] == "high"


def test_priority_has_no_direct_trade_command():
    result = calculate_sector_stock_priority(
        sector_score=50,
        technical_score=50,
    )

    assert "buy" not in result
    assert "sell" not in result
    assert "signal" not in result
