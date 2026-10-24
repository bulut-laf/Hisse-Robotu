from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from .daily_developments import (
    DailyDevelopment,
    build_daily_developments_brief,
)
from .economic_calendar import (
    CalendarImportance,
    EconomicCalendarEntry,
)
from .portfolio_impact import (
    PortfolioMember,
    build_portfolio_impact_radar,
)
from .sector_impact import build_sector_impact_map
from .models import MarketEvent, NewsRecord, SourceTier
from .source_registry import resolve_source


ISTANBUL = ZoneInfo("Europe/Istanbul")


@dataclass(frozen=True, slots=True)
class DayEndSummary:
    selected_date: date
    top_developments: tuple[DailyDevelopment, ...]
    total_event_count: int
    high_importance_event_count: int
    tier1_event_count: int
    multi_source_event_count: int
    news_published_count: int
    kap_disclosure_count: int
    symbol_event_count: int
    unique_symbol_count: int
    sector_count: int
    affected_portfolio_symbol_count: int
    direct_portfolio_hit_count: int
    calendar_event_count: int
    calendar_high_critical_count: int
    calendar_announced_count: int
    calendar_waiting_count: int
    top_sectors: tuple[str, ...]
    affected_portfolio_symbols: tuple[str, ...]


def _require_date(value: date) -> date:
    if not isinstance(value, date):
        raise ValueError("selected_date geçerli bir tarih olmalıdır.")
    return value


def _require_aware(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} datetime olmalıdır.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} saat dilimi içermelidir.")
    return value


def _local_date(value: datetime, field_name: str) -> date:
    return _require_aware(value, field_name).astimezone(ISTANBUL).date()


def _is_verified_kap(news: NewsRecord) -> bool:
    resolution = resolve_source(news.source_name, news.source_reference)
    return resolution is not None and resolution.canonical_name == "KAP"


def build_day_end_summary(
    events: tuple[MarketEvent, ...],
    news: tuple[NewsRecord, ...],
    calendar_entries: tuple[EconomicCalendarEntry, ...],
    *,
    selected_date: date,
    portfolio_members: tuple[PortfolioMember, ...] = (),
    top_limit: int = 10,
) -> DayEndSummary:
    """
    Seçilen gün için deterministik kapanış özeti üretir.

    Yeni bir skor üretmez. Olay öneminde mevcut 0-100 skoru kullanılır.
    Haber/KAP/hisse/sektör/portföy/takvim metrikleri ayrı tutulur.
    Fiyat yönü, AL/SAT, teknik skor veya AI yorumu üretilmez.
    """

    selected_date = _require_date(selected_date)
    if not isinstance(top_limit, int) or not 1 <= top_limit <= 25:
        raise ValueError("top_limit 1-25 aralığında tam sayı olmalıdır.")

    end_of_day = datetime.combine(
        selected_date,
        time.max,
        tzinfo=ISTANBUL,
    )

    day_events = tuple(
        event
        for event in events
        if _local_date(event.occurred_at, "Olay zamanı") == selected_date
    )
    day_event_ids = {event.event_id for event in day_events}

    as_of_news: list[NewsRecord] = []
    day_news: list[NewsRecord] = []
    for item in news:
        published_at = _require_aware(item.published_at, "Haber yayın zamanı")
        local_published = published_at.astimezone(ISTANBUL)
        if local_published <= end_of_day:
            as_of_news.append(item)
        if local_published.date() == selected_date:
            day_news.append(item)

    news_by_event: dict[str, tuple[NewsRecord, ...]] = {}
    for event in day_events:
        news_by_event[event.event_id] = tuple(
            item
            for item in as_of_news
            if item.event_id == event.event_id
        )

    developments = build_daily_developments_brief(
        day_events,
        news_by_event,
        selected_date=selected_date,
        min_importance=0,
        portfolio_members=portfolio_members,
    )

    sector_map = build_sector_impact_map(
        day_events,
        dict(news_by_event),
    )

    if portfolio_members:
        portfolio_radar = build_portfolio_impact_radar(
            day_events,
            news_by_event,
            portfolio_members,
        )
        affected_portfolio_symbols = portfolio_radar.affected_symbols
        direct_portfolio_hit_count = portfolio_radar.direct_symbol_hit_count
    else:
        affected_portfolio_symbols = ()
        direct_portfolio_hit_count = 0

    symbol_events = tuple(event for event in day_events if event.symbols)
    unique_symbols = {
        symbol
        for event in symbol_events
        for symbol in event.symbols
    }

    day_calendar = tuple(
        item
        for item in calendar_entries
        if _local_date(item.scheduled_at, "Takvim zamanı") == selected_date
    )

    calendar_high_critical = sum(
        item.importance in (CalendarImportance.HIGH, CalendarImportance.CRITICAL)
        for item in day_calendar
    )
    calendar_announced = sum(bool(item.actual_value) for item in day_calendar)
    calendar_waiting = sum(
        not item.actual_value
        and item.scheduled_at.astimezone(ISTANBUL) <= end_of_day
        for item in day_calendar
    )

    tier1_event_ids: set[str] = set()
    multi_source_event_ids: set[str] = set()
    for event_id in day_event_ids:
        event_news = news_by_event.get(event_id, ())
        if any(
            item.source_tier is SourceTier.TIER_1_OFFICIAL
            or (
                (resolution := resolve_source(item.source_name, item.source_reference))
                is not None
                and resolution.tier is SourceTier.TIER_1_OFFICIAL
            )
            for item in event_news
        ):
            tier1_event_ids.add(event_id)

        source_labels: set[str] = set()
        for item in event_news:
            resolution = resolve_source(item.source_name, item.source_reference)
            if resolution is not None:
                label = resolution.canonical_name
            else:
                label = str(item.source_name or "").strip().casefold()
            if label:
                source_labels.add(label)
        if len(source_labels) >= 2:
            multi_source_event_ids.add(event_id)

    kap_count = sum(_is_verified_kap(item) for item in day_news)

    top_sectors = tuple(
        item.sector
        for item in sector_map.summaries[:5]
    )

    return DayEndSummary(
        selected_date=selected_date,
        top_developments=developments.developments[:top_limit],
        total_event_count=len(day_events),
        high_importance_event_count=sum(
            event.importance_score >= 80 for event in day_events
        ),
        tier1_event_count=len(tier1_event_ids),
        multi_source_event_count=len(multi_source_event_ids),
        news_published_count=len(day_news),
        kap_disclosure_count=kap_count,
        symbol_event_count=len(symbol_events),
        unique_symbol_count=len(unique_symbols),
        sector_count=sector_map.sector_count,
        affected_portfolio_symbol_count=len(affected_portfolio_symbols),
        direct_portfolio_hit_count=direct_portfolio_hit_count,
        calendar_event_count=len(day_calendar),
        calendar_high_critical_count=calendar_high_critical,
        calendar_announced_count=calendar_announced,
        calendar_waiting_count=calendar_waiting,
        top_sectors=top_sectors,
        affected_portfolio_symbols=affected_portfolio_symbols,
    )


def day_end_development_rows(
    summary: DayEndSummary,
) -> list[dict[str, object]]:
    return [
        {
            "Saat": item.occurred_at.astimezone(ISTANBUL).strftime("%H:%M"),
            "Önem": item.importance_score,
            "Olay": item.event_title,
            "Tür": item.event_type,
            "Kapsam": item.market_scope,
            "Kaynak": item.source_count,
            "Birincil kaynak": "Var" if item.has_tier1_source else "—",
            "Sektörler": ", ".join(item.sector_targets) or "—",
            "Hisseler": ", ".join(item.symbol_targets) or "—",
            "Portföy teması": ", ".join(item.portfolio_symbols) or "—",
        }
        for item in summary.top_developments
    ]


def day_end_metric_rows(
    summary: DayEndSummary,
) -> list[dict[str, object]]:
    return [
        {"Başlık": "Piyasa olayı", "Değer": summary.total_event_count},
        {"Başlık": "Önem ≥80", "Değer": summary.high_importance_event_count},
        {"Başlık": "Gün içi haber", "Değer": summary.news_published_count},
        {"Başlık": "KAP bildirimi", "Değer": summary.kap_disclosure_count},
        {"Başlık": "Hisse olayları", "Değer": summary.symbol_event_count},
        {"Başlık": "Etkilenen sektör", "Değer": summary.sector_count},
        {
            "Başlık": "Portföye temas eden hisse",
            "Değer": summary.affected_portfolio_symbol_count,
        },
        {"Başlık": "Takvim olayı", "Değer": summary.calendar_event_count},
    ]
