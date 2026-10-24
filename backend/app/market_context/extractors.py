from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ExtractedMarketContextInput:
    input_type: str
    raw_text: str
    source_name: str | None = None
    original_filename: str | None = None


class MarketContextExtractionError(ValueError):
    """Girdi metne dönüştürülemediğinde yükseltilir."""


class MarketContextExtractor:
    """Manuel metin, TXT ve PDF girdilerini ortak metin biçimine dönüştürür."""

    @staticmethod
    def from_text(
        text: str,
        *,
        source_name: str | None = None,
    ) -> ExtractedMarketContextInput:
        value = text.strip()
        if not value:
            raise MarketContextExtractionError("Metin boş olamaz.")

        return ExtractedMarketContextInput(
            input_type="text",
            raw_text=value,
            source_name=source_name,
        )

    @staticmethod
    def from_txt(
        path: str | Path,
        *,
        source_name: str | None = None,
    ) -> ExtractedMarketContextInput:
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(source)
        if source.suffix.lower() != ".txt":
            raise MarketContextExtractionError("Dosya TXT formatında olmalıdır.")

        text = source.read_text(encoding="utf-8-sig").strip()
        if not text:
            raise MarketContextExtractionError("TXT dosyası boş.")

        return ExtractedMarketContextInput(
            input_type="txt",
            raw_text=text,
            source_name=source_name,
            original_filename=source.name,
        )

    @staticmethod
    def from_pdf(
        path: str | Path,
        *,
        source_name: str | None = None,
    ) -> ExtractedMarketContextInput:
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(source)
        if source.suffix.lower() != ".pdf":
            raise MarketContextExtractionError("Dosya PDF formatında olmalıdır.")

        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise MarketContextExtractionError(
                "PDF desteği için pypdf paketi gereklidir."
            ) from exc

        try:
            reader = PdfReader(str(source))
            pages: list[str] = []
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text.strip())
        except Exception as exc:
            raise MarketContextExtractionError(
                f"PDF metni okunamadı: {source.name}"
            ) from exc

        raw_text = "\n\n".join(pages).strip()
        if not raw_text:
            raise MarketContextExtractionError(
                "PDF içinde okunabilir metin bulunamadı."
            )

        return ExtractedMarketContextInput(
            input_type="pdf",
            raw_text=raw_text,
            source_name=source_name,
            original_filename=source.name,
        )
