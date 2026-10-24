from backend.app.sector_analysis.ai_sector_comment import (
    generate_sector_comment,
)


def test_ai_sector_comment_generation():
    result = generate_sector_comment(
        {
            "top_sectors": [
                {
                    "name": "Bankacılık",
                    "score": 8,
                }
            ]
        }
    )

    assert result["count"] == 1
    assert result["comments"][0]["sector"] == "Bankacılık"


def test_ai_sector_comment_has_no_trade_logic():
    result = generate_sector_comment(
        {
            "top_sectors": []
        }
    )

    assert "signal" not in result
    assert "buy" not in str(result)
    assert "sell" not in str(result)
