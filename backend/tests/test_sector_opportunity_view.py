from backend.app.sector_analysis.sector_opportunity_view import (
    build_sector_opportunity_view,
)


def test_sector_opportunity_view():
    result = build_sector_opportunity_view(
        [
            {
                "sector": "Sanayi",
                "strength_score": 70,
            },
            {
                "sector": "Bankacılık",
                "strength_score": 85,
            },
        ]
    )

    assert result[0]["sector"] == "Bankacılık"
    assert result[1]["sector"] == "Sanayi"


def test_sector_opportunity_view_empty():
    result = build_sector_opportunity_view([])

    assert result == []
