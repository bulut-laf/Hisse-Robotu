from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re
from typing import Callable
from uuid import uuid4

from .archive import EventNotFoundError, NewsArchive
from .grouping import EventMatch, GroupingDecision, best_event_match
from .importance import calculate_importance
from .models import (
    EventType,
    MarketEvent,
    MarketScope,
    NewsRecord,
    SourceTier,
    normalize_body,
    normalize_optional_text,
    normalize_sectors,
    normalize_symbols,
    normalize_text,
)


class NewsCenterServiceError(RuntimeError):
    """Manuel Haber Merkezi işlemi tamamlanamadığında oluşur."""


class EventGroupingReviewRequired(NewsCenterServiceError):
    """Benzer olay bulunduğunda kullanıcı kararı gerektiğini bildirir."""

    def __init__(self, match: EventMatch) -> None:
        self.match = match
        reasons = " ".join(match.reasons)
        super().__init__(
            "Benzer bir olay bulundu ancak güvenli otomatik birleştirme eşiği "
            f"sağlanmadı: {match.event_title} [{match.event_id}]. {reasons} "
            "Mevcut olaya haber bağla seçeneğini kullanın veya gerçekten ayrı "
            "bir olay ise güvenli olay eşleştirmesini kapatıp tekrar kaydedin."
        )


NowProvider = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class ManualNewsRequest:
    source_name: str
    source_tier: SourceTier
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

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_name",
            normalize_text(self.source_name, field_name="Kaynak adı"),
        )
        object.__setattr__(
            self,
            "headline",
            normalize_text(self.headline, field_name="Haber başlığı"),
        )
        object.__setattr__(self, "body", normalize_body(self.body))
        object.__setattr__(
            self,
            "source_reference",
            normalize_optional_text(self.source_reference),
        )
        object.__setattr__(
            self,
            "event_title",
            normalize_optional_text(self.event_title),
        )
        object.__setattr__(
            self,
            "source_tier",
            SourceTier(self.source_tier),
        )
        object.__setattr__(
            self,
            "event_type",
            EventType(self.event_type),
        )
        object.__setattr__(
            self,
            "market_scope",
            MarketScope(self.market_scope),
        )
        object.__setattr__(
            self,
            "sectors",
            normalize_sectors(self.sectors),
        )
        object.__setattr__(
            self,
            "symbols",
            normalize_symbols(self.symbols),
        )
        if (
            self.published_at.tzinfo is None
            or self.published_at.utcoffset() is None
        ):
            raise ValueError("Yayın zamanı saat dilimi içermelidir.")
        occurred_at = self.occurred_at or self.published_at
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise ValueError("Olay zamanı saat dilimi içermelidir.")
        object.__setattr__(self, "occurred_at", occurred_at)


@dataclass(frozen=True, slots=True)
class ManualArchiveResult:
    event: MarketEvent
    news: NewsRecord
    attached_to_existing_event: bool
    grouped_automatically: bool = False
    grouping_reasons: tuple[str, ...] = ()


class NewsCenterService:
    def __init__(
        self,
        archive: NewsArchive | None = None,
        *,
        now_provider: NowProvider | None = None,
    ) -> None:
        self.archive = archive or NewsArchive()
        self._now_provider = now_provider or (
            lambda: datetime.now(timezone.utc)
        )

    def find_event_match(self, request: ManualNewsRequest) -> EventMatch | None:
        return best_event_match(
            requested_title=request.event_title or request.headline,
            event_type=request.event_type,
            market_scope=request.market_scope,
            occurred_at=request.occurred_at,
            symbols=request.symbols,
            source_reference=request.source_reference,
            events=self.archive.list_events(limit=1000),
            news=self.archive.list_news(limit=5000),
        )

    def submit_manual(
        self,
        request: ManualNewsRequest,
        *,
        existing_event_id: str | None = None,
        auto_group: bool = False,
    ) -> ManualArchiveResult:
        archived_at = self._now_provider()
        if archived_at.tzinfo is None or archived_at.utcoffset() is None:
            raise NewsCenterServiceError(
                "Arşiv zamanı saat dilimi içermelidir."
            )

        event_id = str(existing_event_id or "").strip()
        if event_id:
            return self._attach_to_existing(
                request=request,
                event_id=event_id,
                archived_at=archived_at,
                grouped_automatically=False,
                grouping_reasons=(),
            )

        if auto_group:
            match = self.find_event_match(request)
            if match is not None:
                if match.decision is GroupingDecision.AUTO_ATTACH:
                    return self._attach_to_existing(
                        request=request,
                        event_id=match.event_id,
                        archived_at=archived_at,
                        grouped_automatically=True,
                        grouping_reasons=match.reasons,
                    )
                raise EventGroupingReviewRequired(match)

        event_id = uuid4().hex
        breakdown = calculate_importance(
            source_tier=request.source_tier,
            market_scope=request.market_scope,
            event_type=request.event_type,
            occurred_at=request.occurred_at,
            published_at=request.published_at,
        )
        event = MarketEvent(
            event_id=event_id,
            title=request.event_title or request.headline,
            event_type=request.event_type,
            occurred_at=request.occurred_at,
            market_scope=request.market_scope,
            sectors=request.sectors,
            symbols=request.symbols,
            importance_score=breakdown.total,
            importance_breakdown=breakdown,
        )
        news = self._build_news(
            event_id=event_id,
            request=request,
            archived_at=archived_at,
        )
        self.archive.archive_new_event(
            event,
            news,
            created_at=archived_at,
        )
        return ManualArchiveResult(
            event=self.archive.get_event(event_id),
            news=news,
            attached_to_existing_event=False,
        )

    def _attach_to_existing(
        self,
        *,
        request: ManualNewsRequest,
        event_id: str,
        archived_at: datetime,
        grouped_automatically: bool,
        grouping_reasons: tuple[str, ...],
    ) -> ManualArchiveResult:
        try:
            existing_event = self.archive.get_event(event_id)
        except EventNotFoundError as exc:
            raise NewsCenterServiceError(str(exc)) from exc

        news = self._build_news(
            event_id=event_id,
            request=request,
            archived_at=archived_at,
        )
        candidate = calculate_importance(
            source_tier=request.source_tier,
            market_scope=existing_event.market_scope,
            event_type=existing_event.event_type,
            occurred_at=existing_event.occurred_at,
            published_at=request.published_at,
        )
        updated_event = self.archive.attach_news(
            event_id,
            news,
            candidate_importance=candidate,
        )
        return ManualArchiveResult(
            event=updated_event,
            news=news,
            attached_to_existing_event=True,
            grouped_automatically=grouped_automatically,
            grouping_reasons=grouping_reasons,
        )

    def _build_news(
        self,
        *,
        event_id: str,
        request: ManualNewsRequest,
        archived_at: datetime,
    ) -> NewsRecord:
        return NewsRecord(
            news_id=uuid4().hex,
            event_id=event_id,
            source_name=request.source_name,
            source_tier=request.source_tier,
            headline=request.headline,
            published_at=request.published_at,
            body=request.body,
            source_reference=request.source_reference,
            content_hash=self.content_hash(request),
            archived_at=archived_at,
        )

    @staticmethod
    def content_hash(request: ManualNewsRequest) -> str:
        canonical = "\n".join(
            (
                request.source_name.casefold(),
                request.published_at.isoformat(),
                re.sub(r"\s+", " ", request.headline).strip().casefold(),
                re.sub(r"\s+", " ", request.body).strip(),
            )
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def event_rows(events: tuple[MarketEvent, ...]) -> list[dict[str, object]]:
    return [
        {
            "Olay zamanı": item.occurred_at.isoformat(timespec="minutes"),
            "Önem": item.importance_score,
            "Olay": item.title,
            "Tür": item.event_type.value,
            "Kapsam": item.market_scope.value,
            "Sektörler": ", ".join(item.sectors) or "—",
            "Hisseler": ", ".join(item.symbols) or "—",
            "Kaynak sayısı": len(item.news_ids),
            "Olay kimliği": item.event_id,
        }
        for item in events
    ]


def news_rows(news: tuple[NewsRecord, ...]) -> list[dict[str, object]]:
    return [
        {
            "Yayın zamanı": item.published_at.isoformat(timespec="minutes"),
            "Kaynak": item.source_name,
            "Kaynak seviyesi": item.source_tier.value,
            "Başlık": item.headline,
            "Olay kimliği": item.event_id,
            "Referans": item.source_reference or "—",
            "Haber kimliği": item.news_id,
        }
        for item in news
    ]
