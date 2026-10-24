from backend.app.market_context.parser import MarketContextParser


SAMPLE = """
BIST100 endeksinin güne temkinli ancak pozitif bir başlangıç yapmasını bekliyoruz.
Ağustos vadeli BIST30 kontratı cuma akşam seansını 27 puan artıda tamamladı.
Asya piyasaları ve ABD vadeli endeksleri pozitif seyrediyor.
BIST100 için 13.200 ve 12.966 destek;
13.635–13.721, 13.872–14.085 ve 14.228 direnç olarak izleniyor.
"""


def test_sample_market_bulletin_is_structured():
    result = MarketContextParser().parse(SAMPLE)

    assert result.index_outlook == "Temkinli / Pozitif"
    assert "13.200" in result.supports
    assert "12.966" in result.supports
    assert "13.635–13.721" in result.resistances
    assert "13.872–14.085" in result.resistances
    assert "14.228" in result.resistances
    assert result.external_market_outlook == "Pozitif"
    assert result.futures_outlook == "Pozitif"


def test_macro_risk_sentence_is_preserved():
    text = (
        "Küresel piyasalar yatay. "
        "Enflasyon verisi ve merkez bankası faiz kararı risk oluşturuyor."
    )

    result = MarketContextParser().parse(text)

    assert len(result.macro_risks) == 1
    assert "Enflasyon" in result.macro_risks[0]


def test_sector_sentence_is_preserved():
    result = MarketContextParser().parse(
        "Bankacılık sektörü pozitif ayrışabilir."
    )

    assert result.sector_impacts[0]["sector"] == "Bankacılık"


def test_stock_symbol_sentence_is_preserved():
    result = MarketContextParser().parse(
        "THYAO yeni uçak finansmanına ilişkin KAP açıklaması yayımladı."
    )

    assert result.stock_news[0]["symbol"] == "THYAO"


def test_parser_does_not_create_trading_score():
    result = MarketContextParser().parse(SAMPLE)

    assert not hasattr(result, "technical_score")
    assert not hasattr(result, "buy_signal")
    assert not hasattr(result, "candidate_rank")
