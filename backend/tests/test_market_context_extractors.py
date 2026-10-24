import pytest

from backend.app.market_context.extractors import (
    MarketContextExtractionError,
    MarketContextExtractor,
)


def test_manual_text_extraction():
    item = MarketContextExtractor.from_text(
        "BIST100 pozitif.",
        source_name="ICBC",
    )

    assert item.input_type == "text"
    assert item.raw_text == "BIST100 pozitif."
    assert item.source_name == "ICBC"


def test_empty_manual_text_is_rejected():
    with pytest.raises(MarketContextExtractionError):
        MarketContextExtractor.from_text("   ")


def test_txt_extraction_utf8_sig(tmp_path):
    path = tmp_path / "bulten.txt"
    path.write_text(
        "\ufeffBIST100 güne pozitif başlayabilir.",
        encoding="utf-8",
    )

    item = MarketContextExtractor.from_txt(path)

    assert item.input_type == "txt"
    assert "pozitif" in item.raw_text
    assert item.original_filename == "bulten.txt"


def test_non_txt_file_is_rejected_by_txt_extractor(tmp_path):
    path = tmp_path / "bulten.csv"
    path.write_text("x", encoding="utf-8")

    with pytest.raises(MarketContextExtractionError):
        MarketContextExtractor.from_txt(path)
