from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo

from .models import MarketEvent, NewsRecord, SourceTier
from .source_registry import resolve_source


ISTANBUL = ZoneInfo("Europe/Istanbul")


@dataclass(frozen=True, slots=True)
class SymbolNewsItem:
    symbol: str
    event_id: str
    event_title: str
    event_type: str
    occurred_at: datetime
    latest_published_at: datetime
    importance_score: int
    sectors: tuple[str, ...]
    news_count: int
    source_count: int
    source_names: tuple[str, ...]
    tier1_source_count: int
    kap_news_count: int
    latest_headline: str
    is_portfolio_symbol: bool

    @property
    def is_high_importance(self) -> bool:
        return self.importance_score >= 80

    @property
    def is_multi_source(self) -> bool:
        return self.source_count >= 2

    @property
    def has_tier1_source(self) -> bool:
        return self.tier1_source_count >= 1

    @property
    def has_kap(self) -> bool:
        return self.kap_news_count >= 1


@dataclass(frozen=True, slots=True)
class SymbolNewsBrief:
    items: tuple[SymbolNewsItem, ...]
    unique_symbol_count: int
    unique_event_count: int
    high_importance_event_count: int
    multi_source_event_count: int
    tier1_event_count: int
    kap_event_count: int
    portfolio_symbol_count: int


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


def _source_label(news: NewsRecord) -> str:
    resolution = resolve_source(news.source_name, news.source_reference)
    if resolution is not None:
        return resolution.canonical_name
    return str(news.source_name or "").strip() or "Bilinmeyen"


def symbol_news_available_symbols(events: tuple[MarketEvent, ...]) -> tuple[str, ...]:
    """Yalnız olay kaydında açıkça etiketlenmiş hisse sembollerini döndürür."""

    return tuple(sorted({symbol for event in events for symbol in event.symbols}))


def build_symbol_news_brief(
    events: tuple[MarketEvent, ...],
    news: tuple[NewsRecord, ...],
    *,
    now: datetime,
    lookback_hours: int | None = 168,
    min_importance: int = 0,
    symbol_filter: str = "",
    portfolio_symbols: tuple[str, ...] = (),
    portfolio_only: bool = False,
) -> SymbolNewsBrief:
    """Hisse bazlı haber görünümünü deterministik olarak oluşturur.

    Bir olay + bir hisse tek satırdır. Aynı olayın birden fazla haber kaynağı
    satırı çoğaltmaz; haber ve kaynak sayıları satır içinde özetlenir.
    Hisse sembolleri yalnız `MarketEvent.symbols` alanından gelir; haber metninden
    sembol tahmini yapılmaz. Yeni skor, fiyat yönü, AL/SAT veya AI yorumu üretmez.
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

    normalized_filter = _normalize_symbol(symbol_filter)
    normalized_portfolio = tuple(
        dict.fromkeys(
            symbol
            for symbol in (_normalize_symbol(item) for item in portfolio_symbols)
            if symbol
        )
    )
    portfolio_set = set(normalized_portfolio)

    news_by_event: dict[str, list[NewsRecord]] = {}
    for item in news:
        published_at = _require_aware(item.published_at, "Haber yayın zamanı")
        if published_at > now:
            continue
        news_by_event.setdefault(item.event_id, []).append(item)

    result: list[SymbolNewsItem] = []

    for event in events:
        if not event.symbols:
            continue
        if event.importance_score < min_importance:
            continue

        event_news = news_by_event.get(event.event_id, [])
        if not event_news:
            continue

        latest_news = max(
            event_news,
            key=lambda item: (item.published_at.timestamp(), item.news_id),
        )
        latest_at = _require_aware(latest_news.published_at, "Son haber yayın zamanı")
        if cutoff is not None and latest_at < cutoff:
            continue

        source_names = tuple(sorted({_source_label(item) for item in event_news}, key=str.casefold))
        tier1_source_count = len(
            {
                _source_label(item)
                for item in event_news
                if item.source_tier is SourceTier.TIER_1_OFFICIAL
                or (
                    (resolution := resolve_source(item.source_name, item.source_reference))
                    is not None
                    and resolution.tier is SourceTier.TIER_1_OFFICIAL
                )
            }
        )
        kap_news_count = sum(
            1
            for item in event_news
            if (
                (resolution := resolve_source(item.source_name, item.source_reference))
                is not None
                and resolution.canonical_name == "KAP"
            )
        )

        for symbol in event.symbols:
            if normalized_filter and symbol != normalized_filter:
                continue
            is_portfolio_symbol = symbol in portfolio_set
            if portfolio_only and not is_portfolio_symbol:
                continue

            result.append(
                SymbolNewsItem(
                    symbol=symbol,
                    event_id=event.event_id,
                    event_title=event.title,
                    event_type=event.event_type.value,
                    occurred_at=event.occurred_at,
                    latest_published_at=latest_at,
                    importance_score=event.importance_score,
                    sectors=event.sectors,
                    news_count=len(event_news),
                    source_count=len(source_names),
                    source_names=source_names,
                    tier1_source_count=tier1_source_count,
                    kap_news_count=kap_news_count,
                    latest_headline=latest_news.headline,
                    is_portfolio_symbol=is_portfolio_symbol,
                )
            )

    result.sort(
        key=lambda item: (
            -item.latest_published_at.timestamp(),
            -item.importance_score,
            item.symbol,
            item.event_id,
        )
    )
    ordered = tuple(result)

    unique_event_ids = {item.event_id for item in ordered}

    def _event_ids(predicate) -> set[str]:
        return {item.event_id for item in ordered if predicate(item)}

    return SymbolNewsBrief(
        items=ordered,
        unique_symbol_count=len({item.symbol for item in ordered}),
        unique_event_count=len(unique_event_ids),
        high_importance_event_count=len(_event_ids(lambda item: item.is_high_importance)),
        multi_source_event_count=len(_event_ids(lambda item: item.is_multi_source)),
        tier1_event_count=len(_event_ids(lambda item: item.has_tier1_source)),
        kap_event_count=len(_event_ids(lambda item: item.has_kap)),
        portfolio_symbol_count=len({item.symbol for item in ordered if item.is_portfolio_symbol}),
    )


def symbol_news_rows(brief: SymbolNewsBrief) -> list[dict[str, object]]:
    return [
        {
            "Son yayın": item.latest_published_at.astimezone(ISTANBUL).strftime(
                "%Y-%m-%d %H:%M"
            ),
            "Hisse": item.symbol,
            "Önem": item.importance_score,
            "Portföy": "Evet" if item.is_portfolio_symbol else "—",
            "Tür": item.event_type,
            "Olay": item.event_title,
            "Son başlık": item.latest_headline,
            "Haber": item.news_count,
            "Kaynak": item.source_count,
            "Kaynaklar": ", ".join(item.source_names) or "—",
            "Birincil kaynak": "Var" if item.has_tier1_source else "—",
            "KAP": "Var" if item.has_kap else "—",
            "Sektör": ", ".join(item.sectors) or "—",
            "Olay zamanı": item.occurred_at.astimezone(ISTANBUL).strftime(
                "%Y-%m-%d %H:%M"
            ),
            "Olay kimliği": item.event_id,
        }
        for item in brief.items
    ]
