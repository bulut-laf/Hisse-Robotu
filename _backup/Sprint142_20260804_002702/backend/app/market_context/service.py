from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .extractors import (
    ExtractedMarketContextInput,
    MarketContextExtractor,
)
from .models import MarketContextDocument
from .report_date_detection import detect_report_date
from .source_normalization import normalize_source_name
from .parser import MarketContextParser
from .store import MarketContextStore


class MarketContextDateMismatchError(ValueError):
    """Belgedeki açık rapor tarihi seçilen arşiv tarihiyle uyuşmadığında yükseltilir."""

    def __init__(self, *, selected_date: str, detected_date: str):
        self.selected_date = selected_date
        self.detected_date = detected_date
        super().__init__(
            f"Belgede {detected_date} tarihi algılandı; seçili tarih {selected_date}. "
            "Yanlış güne arşivlemeyi önlemek için tarih alanını kontrol edin."
        )


class MarketContextService:
    """Girdi -> çıkarım -> ayrıştırma -> belge -> arşiv akışını yönetir."""

    def __init__(
        self,
        *,
        data_root: str | Path,
        parser: MarketContextParser | None = None,
    ):
        self.store = MarketContextStore(data_root)
        self.parser = parser or MarketContextParser()

    def import_text(
        self,
        *,
        text: str,
        source: str,
        document_date: str,
        document_id: str | None = None,
    ) -> MarketContextDocument:
        extracted = MarketContextExtractor.from_text(
            text,
            source_name=source,
        )
        return self._persist_extracted(
            extracted=extracted,
            source=source,
            document_date=document_date,
            document_id=document_id,
            raw_extension=".txt",
        )

    def import_txt(
        self,
        *,
        path: str | Path,
        source: str,
        document_date: str,
        document_id: str | None = None,
    ) -> MarketContextDocument:
        extracted = MarketContextExtractor.from_txt(
            path,
            source_name=source,
        )
        return self._persist_extracted(
            extracted=extracted,
            source=source,
            document_date=document_date,
            document_id=document_id,
            raw_extension=".txt",
        )

    def import_pdf(
        self,
        *,
        path: str | Path,
        source: str,
        document_date: str,
        document_id: str | None = None,
    ) -> MarketContextDocument:
        extracted = MarketContextExtractor.from_pdf(
            path,
            source_name=source,
        )

        document = self._build_document(
            extracted=extracted,
            source=source,
            document_date=document_date,
            document_id=document_id,
        )

        saved = self.store.save_text_document(
            document,
            raw_extension=".txt",
        )

        # PDF'nin özgün hali ayrıca ham arşive korunur.
        self.store.save_binary_raw_file(
            source_path=path,
            document_id=saved.document_id,
            document_date=document_date,
            extension=".pdf",
        )

        return saved

    def _persist_extracted(
        self,
        *,
        extracted: ExtractedMarketContextInput,
        source: str,
        document_date: str,
        document_id: str | None,
        raw_extension: str,
    ) -> MarketContextDocument:
        document = self._build_document(
            extracted=extracted,
            source=source,
            document_date=document_date,
            document_id=document_id,
        )
        return self.store.save_text_document(
            document,
            raw_extension=raw_extension,
        )

    def _build_document(
        self,
        *,
        extracted: ExtractedMarketContextInput,
        source: str,
        document_date: str,
        document_id: str | None,
    ) -> MarketContextDocument:
        detected_date = detect_report_date(extracted.raw_text)
        if detected_date and detected_date != document_date:
            raise MarketContextDateMismatchError(
                selected_date=document_date,
                detected_date=detected_date,
            )

        canonical_source = normalize_source_name(source)
        parsed = self.parser.parse(extracted.raw_text)

        return MarketContextDocument(
            document_id=document_id or self._new_document_id(),
            source=canonical_source,
            document_date=document_date,
            imported_at=self._utc_now_iso(),
            input_type=extracted.input_type,
            raw_text=extracted.raw_text,
            content_hash=self.store.content_hash(extracted.raw_text),
            index_outlook=parsed.index_outlook,
            supports=parsed.supports,
            resistances=parsed.resistances,
            external_market_outlook=parsed.external_market_outlook,
            futures_outlook=parsed.futures_outlook,
            macro_risks=parsed.macro_risks,
            sector_impacts=parsed.sector_impacts,
            stock_news=parsed.stock_news,
            notes=parsed.notes,
            archive_date=document_date,
            archive_status="pending",
            ai_eligible=True,
            ai_review_status="not_reviewed",
        )

    @staticmethod
    def _new_document_id() -> str:
        return uuid4().hex

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(UTC).replace(
            microsecond=0
        ).isoformat().replace("+00:00", "Z")
