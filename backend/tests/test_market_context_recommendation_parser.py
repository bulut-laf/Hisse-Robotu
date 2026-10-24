from backend.app.market_context.recommendation_parser import (
    RecommendationParser,
)


def test_weekly_recommendation_is_structured():
    text = """
    AL:
    THYAO
    ASELS

    İZLE:
    EREGL
    SISE

    Hedef fiyat:
    THYAO 350

    Vade:
    1 hafta
    """

    result = RecommendationParser().parse(text)

    assert result.buy == ["THYAO", "ASELS"]
    assert result.watch == ["EREGL", "SISE"]
    assert result.target_prices["THYAO"] == "350"
    assert result.time_horizon == "weekly"


def test_parser_does_not_create_signal():
    result = RecommendationParser().parse("AL:\nTHYAO")

    assert not hasattr(result, "buy_signal")
    assert not hasattr(result, "technical_score")
