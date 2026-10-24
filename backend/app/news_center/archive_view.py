from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re
from zoneinfo import ZoneInfo

from .models import EventType, MarketEvent, MarketScope, NewsRecord, SourceTier
from .source_registry import resolve_source


ISTANBUL = ZoneInfo("Europe/Istanbul")


@dataclass(frozen=True, slots=True)
class ArchiveNewsItem:
    news_id: str
    event_id: str
    headline: str
    published_at: datetime
    archived_at: datetime
    source_name: str
    source_reference: str
    source_is_trusted: bool
    source_is_tier1: bool
    is_kap: bool
    event_found: bool
    event_title: str
    event_type: str
    market_scope: str
    importance_score: int | None
    symbols: tuple[str, ...]
    sectors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArchiveNewsView:
    items: tuple[ArchiveNewsItem, ...]
    news_count: int
    unique_event_count: int
    source_count: int
    tier1_news_count: int
    kap_news_count: int
    symbol_linked_count: int
    unlinked_event_count: int


def _require_aware(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} datetime olmalıdır.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} saat dilimi içermelidir.")
    return value


def _normalize_symbol(value: str) -> str:
    symbol = str(value or "").strip().upper()
    if not symbol:
        return ""
    if "." not in symbol:
        symbol = f"{symbol}.IS"
    if not re.fullmatch(r"[A-Z0-9_]+\.[A-Z0-9_]+", symbol):
        raise ValueError(f"Geçersiz hisse sembolü: {value}")
    return symbol


def _canonical_source(news: NewsRecord) -> tuple[str, bool, bool, bool]:
    resolution = resolve_source(news.source_name, news.source_reference)
    if resolution is None:
        return (
            str(news.source_name or "").strip() or "Bilinmeyen",
            False,
            False,
            False,
        )
    return (
        resolution.canonical_name,
        True,
        resolution.tier is SourceTier.TIER_1_OFFICIAL,
        resolution.canonical_name == "KAP",
    )


def archive_available_sources(
    news: tuple[NewsRecord, ...],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {_canonical_source(item)[0] for item in news},
            key=str.casefold,
        )
    )


def archive_available_symbols(
    events: tuple[MarketEvent, ...],
) -> tuple[str, ...]:
    return tuple(sorted({symbol for event in events for symbol in event.symbols}))


def archive_available_sectors(
    events: tuple[MarketEvent, ...],
) -> tuple[str, ...]:
    sectors: dict[str, str] = {}
    for event in events:
        for sector in event.sectors:
            sectors.setdefault(sector.casefold(), sector)
    return tuple(sorted(sectors.values(), key=str.casefold))


def build_archive_news_view(
    events: tuple[MarketEvent, ...],
    news: tuple[NewsRecord, ...],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    source_filter: str = "",
    symbol_filter: str = "",
    sector_filter: str = "",
    event_type_filter: EventType | str | None = None,
    market_scope_filter: MarketScope | str | None = None,
    min_importance: int = 0,
    text_query: str = "",
    trusted_only: bool = False,
    limit: int = 500,
) -> ArchiveNewsView:
    """
    Haber arşivini deterministik filtrelerle süzer.

    Hisse/sektör/olay türü/önem yalnız bağlı MarketEvent kaydından gelir.
    Haber metninden sembol, sektör veya önem tahmini yapılmaz.
    Yeni skor, fiyat yönü, AL/SAT, teknik skor veya AI yorumu üretilmez.
    """

    if start_date is not None and not isinstance(start_date, date):
        raise ValueError("start_date geçerli bir tarih olmalıdır.")
    if end_date is not None and not isinstance(end_date, date):
        raise ValueError("end_date geçerli bir tarih olmalıdır.")
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")
    if not isinstance(min_importance, int) or not 0 <= min_importance <= 100:
        raise ValueError("min_importance 0-100 aralığında tam sayı olmalıdır.")
    if not isinstance(limit, int) or not 1 <= limit <= 5000:
        raise ValueError("limit 1-5000 aralığında tam sayı olmalıdır.")

    normalized_source = str(source_filter or "").strip().casefold()
    normalized_symbol = _normalize_symbol(symbol_filter)
    normalized_sector = str(sector_filter or "").strip().casefold()
    normalized_query = re.sub(r"\s+", " ", str(text_query or "")).strip().casefold()

    event_type: EventType | None
    if event_type_filter in (None, ""):
        event_type = None
    else:
        event_type = (
            event_type_filter
            if isinstance(event_type_filter, EventType)
            else EventType(event_type_filter)
        )

    market_scope: MarketScope | None
    if market_scope_filter in (None, ""):
        market_scope = None
    else:
        market_scope = (
            market_scope_filter
            if isinstance(market_scope_filter, MarketScope)
            else MarketScope(market_scope_filter)
        )

    event_map = {event.event_id: event for event in events}
    result: list[ArchiveNewsItem] = []

    for item in news:
        published_at = _require_aware(item.published_at, "Haber yayın zamanı")
        archived_at = _require_aware(item.archived_at, "Haber arşiv zamanı")
        local_date = published_at.astimezone(ISTANBUL).date()

        if start_date is not None and local_date < start_date:
            continue
        if end_date is not None and local_date > end_date:
            continue

        source_name, is_trusted, is_tier1, is_kap = _canonical_source(item)
        if trusted_only and not is_trusted:
            continue
        if normalized_source and source_name.casefold() != normalized_source:
            continue

        event = event_map.get(item.event_id)
        if event is None:
            if (
                normalized_symbol
                or normalized_sector
                or event_type is not None
                or market_scope is not None
                or min_importance > 0
            ):
                continue
            event_title = "Bağlı olay bulunamadı"
            event_type_value = "—"
            market_scope_value = "—"
            importance_score = None
            symbols: tuple[str, ...] = ()
            sectors: tuple[str, ...] = ()
        else:
            if normalized_symbol and normalized_symbol not in event.symbols:
                continue
            if normalized_sector and not any(
                sector.casefold() == normalized_sector for sector in event.sectors
            ):
                continue
            if event_type is not None and event.event_type is not event_type:
                continue
            if market_scope is not None and event.market_scope is not market_scope:
                continue
            if event.importance_score < min_importance:
                continue

            event_title = event.title
            event_type_value = event.event_type.value
            market_scope_value = event.market_scope.value
            importance_score = event.importance_score
            symbols = event.symbols
            sectors = event.sectors

        if normalized_query:
            searchable = " ".join(
                (
                    item.headline,
                    item.body,
                    source_name,
                    item.source_reference,
                    event_title,
                )
            ).casefold()
            if normalized_query not in searchable:
                continue

        result.append(
            ArchiveNewsItem(
                news_id=item.news_id,
                event_id=item.event_id,
                headline=item.headline,
                published_at=published_at,
                archived_at=archived_at,
                source_name=source_name,
                source_reference=item.source_reference,
                source_is_trusted=is_trusted,
                source_is_tier1=is_tier1,
                is_kap=is_kap,
                event_found=event is not None,
                event_title=event_title,
                event_type=event_type_value,
                market_scope=market_scope_value,
                importance_score=importance_score,
                symbols=symbols,
                sectors=sectors,
            )
        )

    result.sort(
        key=lambda row: (
            -row.published_at.timestamp(),
            -row.archived_at.timestamp(),
            row.news_id,
        )
    )
    ordered = tuple(result[:limit])

    return ArchiveNewsView(
        items=ordered,
        news_count=len(ordered),
        unique_event_count=len({item.event_id for item in ordered}),
        source_count=len({item.source_name for item in ordered}),
        tier1_news_count=sum(item.source_is_tier1 for item in ordered),
        kap_news_count=sum(item.is_kap for item in ordered),
        symbol_linked_count=sum(bool(item.symbols) for item in ordered),
        unlinked_event_count=sum(not item.event_found for item in ordered),
    )


def archive_news_rows(
    view: ArchiveNewsView,
) -> list[dict[str, object]]:
    return [
        {
            "Yayın": item.published_at.astimezone(ISTANBUL).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "Kaynak": item.source_name,
            "Birincil": "Evet" if item.source_is_tier1 else "—",
            "KAP": "Evet" if item.is_kap else "—",
            "Önem": item.importance_score if item.importance_score is not None else "—",
            "Hisseler": ", ".join(item.symbols) or "—",
            "Sektörler": ", ".join(item.sectors) or "—",
            "Tür": item.event_type,
            "Kapsam": item.market_scope,
            "Başlık": item.headline,
            "Olay": item.event_title,
            "Kaynak referansı": item.source_reference or "—",
            "Haber kimliği": item.news_id,
        }
        for item in view.items
    ]
