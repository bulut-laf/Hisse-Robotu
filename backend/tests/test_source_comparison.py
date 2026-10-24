from backend.app.market_context.source_comparison import SourceComparison


def test_source_comparison_structure():
    data = SourceComparison(
        topic="THYAO",
        positive_views=["Kurumlar olumlu"],
        negative_views=["Petrol riski"],
        risk_notes=["Global belirsizlik"],
    ).to_dict()

    assert data["topic"] == "THYAO"
    assert "Kurumlar olumlu" in data["positive_views"]
    assert "Petrol riski" in data["negative_views"]


def test_source_comparison_has_no_trade_logic():
    data = SourceComparison(topic="BIST").to_dict()

    assert "signal" not in data
    assert "buy" not in data
    assert "technical_score" not in data
