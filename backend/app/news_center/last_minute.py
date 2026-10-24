from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo

from .models import MarketEvent, NewsRecord, SourceTier
from .source_registry import resolve_source


ISTANBUL = ZoneInfo("Europe/Istanbul")


@dataclass(frozen=True, slots=True)
class LastMinuteItem:
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
    event_title: str
    event_type: str
    market_scope: str
    importance_score: int | None
    symbols: tuple[str, ...]
    sectors: tuple[str, ...]
    portfolio_symbols: tuple[str, ...]
    event_found: bool


@dataclass(frozen=True, slots=True)
class LastMinuteBrief:
    items: tuple[LastMinuteItem, ...]
    news_count: int
    unique_event_count: int
    tier1_news_count: int
    kap_news_count: int
    symbol_news_count: int
    portfolio_news_count: int
    unlinked_event_count: int
    latest_published_at: datetime | None


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


def _source_label(news: NewsRecord) -> tuple[str, bool, bool, bool]:
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


def last_minute_available_sources(
    news: tuple[NewsRecord, ...],
) -> tuple[str, ...]:
    labels = {_source_label(item)[0] for item in news}
    return tuple(sorted(labels, key=str.casefold))


def last_minute_available_symbols(
    events: tuple[MarketEvent, ...],
) -> tuple[str, ...]:
    return tuple(sorted({symbol for event in events for symbol in event.symbols}))


def build_last_minute_feed(
    events: tuple[MarketEvent, ...],
    news: tuple[NewsRecord, ...],
    *,
    now: datetime,
    lookback_hours: int | None = 24,
    min_importance: int = 0,
    source_filter: str = "",
    symbol_filter: str = "",
    portfolio_symbols: tuple[str, ...] = (),
    portfolio_only: bool = False,
    trusted_only: bool = True,
    limit: int = 100,
) -> LastMinuteBrief:
    """
    Haber arşivindeki yayınları kronolojik Son Dakika akışına dönüştürür.

    Bir haber kaydı bir satırdır. Aynı olaya daha sonra gelen ikinci kaynak
    ayrı yayın zamanı ile görünür; olay bazında birleştirilmez. Exact duplicate
    engeli arşiv katmanında kalır.

    Yeni skor üretmez; bağlı olay varsa mevcut önem skorunu yalnız gösterir.
    Fiyat yönü, AL/SAT, teknik skor veya AI yorumu üretmez.
    """

    now = _require_aware(now, "now")

    if lookback_hours is not None:
        if not isinstance(lookback_hours, int) or lookback_hours <= 0:
            raise ValueError("lookback_hours pozitif tam sayı veya None olmalıdır.")
        cutoff = now - timedelta(hours=lookback_hours)
    else:
        cutoff = None

    if not isinstance(min_importance, int) or not 0 <= min_importance <= 100:
        raise ValueError("min_importance 0-100 aralığında tam sayı olmalıdır.")
    if not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ValueError("limit 1-500 aralığında tam sayı olmalıdır.")

    normalized_source = str(source_filter or "").strip().casefold()
    normalized_symbol = _normalize_symbol(symbol_filter)
    normalized_portfolio = {
        symbol
        for symbol in (_normalize_symbol(item) for item in portfolio_symbols)
        if symbol
    }

    event_map = {event.event_id: event for event in events}
    result: list[LastMinuteItem] = []

    for item in news:
        published_at = _require_aware(item.published_at, "Haber yayın zamanı")
        archived_at = _require_aware(item.archived_at, "Haber arşiv zamanı")

        if published_at > now:
            continue
        if cutoff is not None and published_at < cutoff:
            continue

        source_name, is_trusted, is_tier1, is_kap = _source_label(item)
        if trusted_only and not is_trusted:
            continue
        if normalized_source and source_name.casefold() != normalized_source:
            continue

        event = event_map.get(item.event_id)
        if event is None:
            if min_importance > 0 or normalized_symbol or portfolio_only:
                continue
            importance_score = None
            event_title = "Bağlı olay bulunamadı"
            event_type = "—"
            market_scope = "—"
            symbols: tuple[str, ...] = ()
            sectors: tuple[str, ...] = ()
            portfolio_hits: tuple[str, ...] = ()
        else:
            importance_score = event.importance_score
            if importance_score < min_importance:
                continue
            symbols = event.symbols
            sectors = event.sectors

            if normalized_symbol and normalized_symbol not in symbols:
                continue

            portfolio_hits = tuple(
                symbol for symbol in symbols if symbol in normalized_portfolio
            )
            if portfolio_only and not portfolio_hits:
                continue

            event_title = event.title
            event_type = event.event_type.value
            market_scope = event.market_scope.value

        result.append(
            LastMinuteItem(
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
                event_title=event_title,
                event_type=event_type,
                market_scope=market_scope,
                importance_score=importance_score,
                symbols=symbols,
                sectors=sectors,
                portfolio_symbols=portfolio_hits,
                event_found=event is not None,
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

    return LastMinuteBrief(
        items=ordered,
        news_count=len(ordered),
        unique_event_count=len({item.event_id for item in ordered}),
        tier1_news_count=sum(item.source_is_tier1 for item in ordered),
        kap_news_count=sum(item.is_kap for item in ordered),
        symbol_news_count=sum(bool(item.symbols) for item in ordered),
        portfolio_news_count=sum(bool(item.portfolio_symbols) for item in ordered),
        unlinked_event_count=sum(not item.event_found for item in ordered),
        latest_published_at=ordered[0].published_at if ordered else None,
    )


def last_minute_rows(
    brief: LastMinuteBrief,
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
            "Portföy": ", ".join(item.portfolio_symbols) or "—",
            "Sektörler": ", ".join(item.sectors) or "—",
            "Başlık": item.headline,
            "Olay": item.event_title,
            "Tür": item.event_type,
            "Kapsam": item.market_scope,
            "Kaynak referansı": item.source_reference or "—",
            "Haber kimliği": item.news_id,
        }
        for item in brief.items
    ]
