from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re
from typing import Callable

from .archive import DuplicateNewsError, NewsArchive, NewsArchiveError
from .models import EventType, MarketScope, SourceTier, normalize_body, normalize_optional_text, normalize_sectors, normalize_symbols, normalize_text
from .service import ManualNewsRequest, NewsCenterService, ManualArchiveResult
from .source_registry import TRUSTED_SOURCES, SourceResolution, resolve_source


class FeedIngestionError(RuntimeError):
    """Güvenilir kaynak besleme hazırlık işlemi başarısız olduğunda oluşur."""


@dataclass(frozen=True, slots=True)
class FeedSourceStatus:
    canonical_name: str
    tier: SourceTier
    domains: tuple[str, ...]
    adapter_enabled: bool = False


@dataclass(frozen=True, slots=True)
class FeedItem:
    source_name: str
    headline: str
    published_at: datetime
    body: str
    source_reference: str = ""
    event_title: str = ""
    event_type: EventType = EventType.DIGER
    occurred_at: datetime | None = None
    market_scope: MarketScope = MarketScope.OTHER
    sectors: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    external_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", normalize_text(self.source_name, field_name="Kaynak adı"))
        object.__setattr__(self, "headline", normalize_text(self.headline, field_name="Haber başlığı"))
        object.__setattr__(self, "body", normalize_body(self.body))
        object.__setattr__(self, "source_reference", normalize_optional_text(self.source_reference))
        object.__setattr__(self, "event_title", normalize_optional_text(self.event_title))
        object.__setattr__(self, "external_id", normalize_optional_text(self.external_id))
        object.__setattr__(self, "event_type", EventType(self.event_type))
        object.__setattr__(self, "market_scope", MarketScope(self.market_scope))
        object.__setattr__(self, "sectors", normalize_sectors(self.sectors))
        object.__setattr__(self, "symbols", normalize_symbols(self.symbols))
        if self.published_at.tzinfo is None or self.published_at.utcoffset() is None:
            raise ValueError("Yayın zamanı saat dilimi içermelidir.")
        occurred_at = self.occurred_at or self.published_at
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise ValueError("Olay zamanı saat dilimi içermelidir.")
        object.__setattr__(self, "occurred_at", occurred_at)


@dataclass(frozen=True, slots=True)
class FeedPreview:
    item: FeedItem
    source: SourceResolution
    content_hash: str
    duplicate: bool
    existing_news_id: str = ""


@dataclass(frozen=True, slots=True)
class FeedImportResult:
    preview: FeedPreview
    archived: bool
    duplicate: bool
    archive_result: ManualArchiveResult | None = None


NowProvider = Callable[[], datetime]


def feed_source_statuses(
    active_adapters: tuple[str, ...] = (),
) -> tuple[FeedSourceStatus, ...]:
    """
    Kayıtlı güvenilir kaynakları ve etkin adapter durumunu gösterir.

    Varsayılan active_adapters=() korunur; böylece hiçbir adapter kendiliğinden
    aktif sayılmaz. UI yalnız açıkça etkinleştirilen adapterleri iletir.
    """
    active = {str(name or "").strip().casefold() for name in active_adapters}
    return tuple(
        FeedSourceStatus(
            canonical_name=item.canonical_name,
            tier=item.tier,
            domains=item.domains,
            adapter_enabled=item.canonical_name.casefold() in active,
        )
        for item in TRUSTED_SOURCES
    )


def _canonical_hash(item: FeedItem, resolution: SourceResolution) -> str:
    canonical = "\n".join(
        (
            resolution.canonical_name.casefold(),
            item.published_at.isoformat(),
            re.sub(r"\s+", " ", item.headline).strip().casefold(),
            re.sub(r"\s+", " ", item.body).strip(),
        )
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class FeedIngestionService:
    """
    Ağdan veri çekmez. Adapter tarafından normalize edilmiş FeedItem kayıtlarını
    güvenilir kaynak sözlüğüne göre doğrular, dry-run önizlemesi üretir ve ancak
    explicit import çağrısında mevcut Haber Merkezi servisinden arşivler.
    """

    def __init__(
        self,
        archive: NewsArchive | None = None,
        *,
        now_provider: NowProvider | None = None,
    ) -> None:
        self.archive = archive or NewsArchive()
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self._service = NewsCenterService(self.archive, now_provider=self._now_provider)

    def _archive_hash_index(self) -> dict[str, str]:
        try:
            existing = self.archive.list_news(limit=10000)
        except (NewsArchiveError, ValueError) as exc:
            raise FeedIngestionError(f"Haber arşivi okunamadı: {exc}") from exc
        return {news.content_hash: news.news_id for news in existing}

    def _preview_with_hash_index(
        self,
        item: FeedItem,
        existing_hashes: dict[str, str],
        *,
        batch_hashes: set[str] | None = None,
    ) -> FeedPreview:
        resolution = resolve_source(item.source_name, item.source_reference)
        if resolution is None:
            raise FeedIngestionError(
                "Kaynak güvenilir kaynak sözlüğünde doğrulanamadı; otomatik besleme için reddedildi."
            )

        digest = _canonical_hash(item, resolution)
        existing_news_id = existing_hashes.get(digest, "")
        duplicate = bool(existing_news_id)
        if batch_hashes is not None:
            if digest in batch_hashes:
                duplicate = True
            else:
                batch_hashes.add(digest)

        return FeedPreview(
            item=item,
            source=resolution,
            content_hash=digest,
            duplicate=duplicate,
            existing_news_id=existing_news_id,
        )

    def preview(self, item: FeedItem) -> FeedPreview:
        return self._preview_with_hash_index(item, self._archive_hash_index())

    def preview_many(self, items: tuple[FeedItem, ...] | list[FeedItem]) -> tuple[FeedPreview, ...]:
        """
        Bir RSS yenilemesindeki kayıtları tek arşiv okumasıyla dry-run eder.

        Aynı içerik aynı yenilemede birden fazla kanalda görünürse ilk kayıt YENİ,
        sonraki kayıtlar aynı-akış tekrarı sayılır. Böylece N haber için N kez tüm
        arşivin okunması engellenir.
        """
        existing_hashes = self._archive_hash_index()
        batch_hashes: set[str] = set()
        return tuple(
            self._preview_with_hash_index(
                item,
                existing_hashes,
                batch_hashes=batch_hashes,
            )
            for item in items
        )

    def import_preview(
        self,
        preview: FeedPreview,
        *,
        existing_event_id: str | None = None,
    ) -> FeedImportResult:
        if preview.duplicate:
            return FeedImportResult(
                preview=preview,
                archived=False,
                duplicate=True,
                archive_result=None,
            )

        item = preview.item
        request = ManualNewsRequest(
            source_name=preview.source.canonical_name,
            source_tier=preview.source.tier,
            headline=item.headline,
            published_at=item.published_at,
            body=item.body,
            source_reference=item.source_reference,
            event_title=item.event_title,
            event_type=item.event_type,
            occurred_at=item.occurred_at,
            market_scope=item.market_scope,
            sectors=item.sectors,
            symbols=item.symbols,
        )

        try:
            result = self._service.submit_manual(
                request,
                existing_event_id=existing_event_id,
            )
        except DuplicateNewsError:
            # Önizleme ile aktarım arasındaki yarışta veritabanı UNIQUE kilidi son savunmadır.
            return FeedImportResult(
                preview=FeedPreview(
                    item=preview.item,
                    source=preview.source,
                    content_hash=preview.content_hash,
                    duplicate=True,
                    existing_news_id=preview.existing_news_id,
                ),
                archived=False,
                duplicate=True,
                archive_result=None,
            )
        except (NewsArchiveError, ValueError, RuntimeError) as exc:
            raise FeedIngestionError(f"Besleme kaydı arşivlenemedi: {exc}") from exc

        return FeedImportResult(
            preview=preview,
            archived=True,
            duplicate=False,
            archive_result=result,
        )

    def import_item(
        self,
        item: FeedItem,
        *,
        existing_event_id: str | None = None,
    ) -> FeedImportResult:
        return self.import_preview(
            self.preview(item),
            existing_event_id=existing_event_id,
        )
