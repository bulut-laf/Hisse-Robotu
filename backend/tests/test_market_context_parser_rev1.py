from backend.app.market_context.parser import MarketContextParser


def test_icbc_levels_are_separated():
    text = """
    BIST100 endeksinin güne temkinli ancak pozitif başlamasını bekliyoruz.
    BIST100 için 13.200 ve 12.966 destek;
    13.635–13.721, 13.872–14.085 ve 14.228 direnç olarak izleniyor.
    """

    result = MarketContextParser().parse(text)

    assert result.supports == ["13.200", "12.966"]
    assert result.resistances == [
        "13.635–13.721",
        "13.872–14.085",
        "14.228",
    ]
    assert "100" not in result.supports
    assert "100" not in result.resistances
