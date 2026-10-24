import pytest

from backend.app.market_context.extractors import (
    MarketContextExtractionError,
    MarketContextExtractor,
)


def test_pdf_extractor_rejects_non_pdf(tmp_path):
    path = tmp_path / "rapor.txt"
    path.write_text("örnek", encoding="utf-8")

    with pytest.raises(MarketContextExtractionError):
        MarketContextExtractor.from_pdf(path)


def test_pdf_extractor_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        MarketContextExtractor.from_pdf(tmp_path / "yok.pdf")
