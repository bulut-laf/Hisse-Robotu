from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable
from zoneinfo import ZoneInfo

from .models import EventType, MarketEvent, NewsRecord, SourceTier, normalize_symbols
from .official_source_operations import (
    OfficialSourceOperationKind,
    OfficialSourceOperationRecord,
)


ISTANBUL = ZoneInfo("Europe/Istanbul")


@dataclass(frozen=True, slots=True)
class DailyOperationsEvent:
    event_id: str
    occurred_at: datetime
    title: str
    importance_score: int
    event_type: EventType
    market_scope: str
    symbols: tuple[str, ...]
    sectors: tuple[str, ...]
    news_count: int
    tier1_news_count: int


@dataclass(frozen=True, slots=True)
class DailyOfficialSourceStatus:
    source_name: str
    news_count: int
    operation_count: int
    preview_success_count: int
    preview_error_count: int
    preview_blocked_count: int
    archive_success_count: int
    archive_duplicate_count: int
    archive_error_count: int
    last_success_at: datetime | None


@dataclass(frozen=True, slots=True)
class DailyNewsOperationsBrief:
    selected_date: date
    event_count: int
    high_importance_event_count: int
    news_count: int
    tier1_news_count: int
    kap_event_count: int
    unique_symbol_count: int
    portfolio_touched_symbols: tuple[str, ...]
    official_sources_used_count: int
    source_operation_count: int
    source_operation_error_count: int
    latest_news_published_at: datetime | None
    latest_source_success_at: datetime | None
    priority_events: tuple[DailyOperationsEvent, ...]
    official_sources: tuple[DailyOfficialSourceStatus, ...]


_ERROR_KINDS = frozenset(
    {
        OfficialSourceOperationKind.PREVIEW_ERROR,
        OfficialSourceOperationKind.ARCHIVE_ERROR,
    }
)

_SUCCESS_KINDS = frozenset(
    {
        OfficialSourceOperationKind.PREVIEW_SUCCESS,
        OfficialSourceOperationKind.ARCHIVE_SUCCESS,
    }
)


def _local_day(value: datetime, timezone: ZoneInfo) -> date:
    return value.astimezone(timezone).date()


def _on_day_and_not_future(
    value: datetime,
    *,
    selected_date: date,
    as_of: datetime,
    timezone: ZoneInfo,
) -> bool:
    if _local_day(value, timezone) != selected_date:
        return False
    return value <= as_of


def build_daily_news_operations_brief(
    events: Iterable[MarketEvent],
    news: Iterable[NewsRecord],
    operations: Iterable[OfficialSourceOperationRecord],
    *,
    selected_date: date,
    official_source_names: Iterable[str],
    portfolio_symbols: Iterable[str] = (),
    as_of: datetime | None = None,
    timezone: ZoneInfo = ISTANBUL,
    priority_limit: int = 10,
) -> DailyNewsOperationsBrief:
    if not isinstance(selected_date, date):
        raise ValueError("selected_date geçerli bir date olmalıdır.")
    if not isinstance(priority_limit, int) or not 1 <= priority_limit <= 50:
        raise ValueError("priority_limit 1-50 aralığında tam sayı olmalıdır.")

    current = as_of or datetime.now(timezone)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("as_of saat dilimi içermelidir.")

    source_names = tuple(
        dict.fromkeys(
            str(item).strip()
            for item in official_source_names
            if str(item).strip()
        )
    )
    portfolio = frozenset(normalize_symbols(tuple(portfolio_symbols)))

    day_events = tuple(
        item
        for item in events
        if _on_day_and_not_future(
            item.occurred_at,
            selected_date=selected_date,
            as_of=current,
            timezone=timezone,
        )
    )

    day_news = tuple(
        item
        for item in news
        if _on_day_and_not_future(
            item.published_at,
            selected_date=selected_date,
            as_of=current,
            timezone=timezone,
        )
    )

    news_by_event: dict[str, list[NewsRecord]] = {}
    for item in day_news:
        news_by_event.setdefault(item.event_id, []).append(item)

    day_operations = tuple(
        item
        for item in operations
        if _on_day_and_not_future(
            item.occurred_at,
            selected_date=selected_date,
            as_of=current,
            timezone=timezone,
        )
    )

    priority_rows: list[DailyOperationsEvent] = []
    touched_symbols: set[str] = set()

    for event in day_events:
        linked_news = tuple(news_by_event.get(event.event_id, ()))
        symbols = tuple(event.symbols)
        touched_symbols.update(symbol for symbol in symbols if symbol in portfolio)
        priority_rows.append(
            DailyOperationsEvent(
                event_id=event.event_id,
                occurred_at=event.occurred_at,
                title=event.title,
                importance_score=event.importance_score,
                event_type=event.event_type,
                market_scope=event.market_scope.value,
                symbols=symbols,
                sectors=tuple(event.sectors),
                news_count=len(linked_news),
                tier1_news_count=sum(
                    item.source_tier is SourceTier.TIER_1_OFFICIAL
                    for item in linked_news
                ),
            )
        )

    priority_rows.sort(
        key=lambda item: (
            -item.importance_score,
            -item.tier1_news_count,
            -item.news_count,
            -item.occurred_at.timestamp(),
            item.title.casefold(),
        )
    )

    official_statuses: list[DailyOfficialSourceStatus] = []
    for source_name in source_names:
        source_news = tuple(
            item for item in day_news if item.source_name == source_name
        )
        source_ops = tuple(
            item for item in day_operations if item.source_name == source_name
        )
        source_successes = tuple(
            item for item in source_ops if item.kind in _SUCCESS_KINDS
        )
        official_statuses.append(
            DailyOfficialSourceStatus(
                source_name=source_name,
                news_count=len(source_news),
                operation_count=len(source_ops),
                preview_success_count=sum(
                    item.kind is OfficialSourceOperationKind.PREVIEW_SUCCESS
                    for item in source_ops
                ),
                preview_error_count=sum(
                    item.kind is OfficialSourceOperationKind.PREVIEW_ERROR
                    for item in source_ops
                ),
                preview_blocked_count=sum(
                    item.kind is OfficialSourceOperationKind.PREVIEW_BLOCKED
                    for item in source_ops
                ),
                archive_success_count=sum(
                    item.kind is OfficialSourceOperationKind.ARCHIVE_SUCCESS
                    for item in source_ops
                ),
                archive_duplicate_count=sum(
                    item.kind is OfficialSourceOperationKind.ARCHIVE_DUPLICATE
                    for item in source_ops
                ),
                archive_error_count=sum(
                    item.kind is OfficialSourceOperationKind.ARCHIVE_ERROR
                    for item in source_ops
                ),
                last_success_at=max(
                    (item.occurred_at for item in source_successes),
                    default=None,
                ),
            )
        )

    latest_news = max(
        (item.published_at for item in day_news),
        default=None,
    )
    latest_source_success = max(
        (
            item.occurred_at
            for item in day_operations
            if item.kind in _SUCCESS_KINDS
        ),
        default=None,
    )

    return DailyNewsOperationsBrief(
        selected_date=selected_date,
        event_count=len(day_events),
        high_importance_event_count=sum(
            item.importance_score >= 80 for item in day_events
        ),
        news_count=len(day_news),
        tier1_news_count=sum(
            item.source_tier is SourceTier.TIER_1_OFFICIAL
            for item in day_news
        ),
        kap_event_count=sum(
            item.event_type is EventType.KAP_ACIKLAMASI
            for item in day_events
        ),
        unique_symbol_count=len(
            {symbol for item in day_events for symbol in item.symbols}
        ),
        portfolio_touched_symbols=tuple(sorted(touched_symbols)),
        official_sources_used_count=sum(
            bool(item.news_count or item.operation_count)
            for item in official_statuses
        ),
        source_operation_count=len(day_operations),
        source_operation_error_count=sum(
            item.kind in _ERROR_KINDS for item in day_operations
        ),
        latest_news_published_at=latest_news,
        latest_source_success_at=latest_source_success,
        priority_events=tuple(priority_rows[:priority_limit]),
        official_sources=tuple(official_statuses),
    )


def daily_operations_event_rows(
    brief: DailyNewsOperationsBrief,
    *,
    timezone: ZoneInfo = ISTANBUL,
) -> list[dict[str, object]]:
    return [
        {
            "Zaman": item.occurred_at.astimezone(timezone).strftime("%H:%M"),
            "Önem": item.importance_score,
            "Olay": item.title,
            "Tür": item.event_type.value,
            "Kapsam": item.market_scope,
            "Hisseler": ", ".join(item.symbols) or "—",
            "Sektörler": ", ".join(item.sectors) or "—",
            "Haber": item.news_count,
            "Birincil haber": item.tier1_news_count,
        }
        for item in brief.priority_events
    ]


def daily_operations_source_rows(
    brief: DailyNewsOperationsBrief,
    *,
    timezone: ZoneInfo = ISTANBUL,
) -> list[dict[str, object]]:
    return [
        {
            "Kaynak": item.source_name,
            "Günlük haber": item.news_count,
            "Operasyon": item.operation_count,
            "Önizleme başarılı": item.preview_success_count,
            "Önizleme hata": item.preview_error_count,
            "Onay bekleyen": item.preview_blocked_count,
            "Arşiv başarılı": item.archive_success_count,
            "Duplicate": item.archive_duplicate_count,
            "Arşiv hata": item.archive_error_count,
            "Son başarılı kullanım": (
                item.last_success_at.astimezone(timezone).strftime("%H:%M:%S")
                if item.last_success_at is not None
                else "—"
            ),
        }
        for item in brief.official_sources
    ]
