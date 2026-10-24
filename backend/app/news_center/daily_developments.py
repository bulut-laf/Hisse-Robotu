from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping
from zoneinfo import ZoneInfo

from .impact import ImpactRelation, ImpactTargetType, assess_event_impact
from .models import MarketEvent, NewsRecord, SourceTier
from .portfolio_impact import (
    PortfolioImpactRadar,
    PortfolioMember,
    build_portfolio_impact_radar,
)


ISTANBUL = ZoneInfo("Europe/Istanbul")


@dataclass(frozen=True, slots=True)
class DailyDevelopment:
    event_id: str
    event_title: str
    occurred_at: datetime
    importance_score: int
    event_type: str
    market_scope: str
    source_count: int
    has_tier1_source: bool
    sector_targets: tuple[str, ...]
    symbol_targets: tuple[str, ...]
    direct_target_count: int
    sensitivity_target_count: int
    portfolio_symbols: tuple[str, ...]

    @property
    def is_high_importance(self) -> bool:
        return self.importance_score >= 80

    @property
    def is_multi_source(self) -> bool:
        return self.source_count >= 2

    @property
    def has_portfolio_touch(self) -> bool:
        return bool(self.portfolio_symbols)


@dataclass(frozen=True, slots=True)
class DailyDevelopmentsBrief:
    selected_date: date
    developments: tuple[DailyDevelopment, ...]
    total_event_count: int
    high_importance_count: int
    tier1_event_count: int
    multi_source_event_count: int
    portfolio_touched_event_count: int


def _local_date(value: datetime) -> date:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Olay zamanı saat dilimi içermelidir.")
    return value.astimezone(ISTANBUL).date()


def _portfolio_hits_by_event(
    radar: PortfolioImpactRadar,
) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for hit in radar.hits:
        values = grouped.setdefault(hit.event_id, [])
        if hit.symbol not in values:
            values.append(hit.symbol)
    return {event_id: tuple(symbols) for event_id, symbols in grouped.items()}


def build_daily_developments_brief(
    events: tuple[MarketEvent, ...],
    news_by_event: Mapping[str, tuple[NewsRecord, ...]],
    *,
    selected_date: date,
    min_importance: int = 70,
    portfolio_members: tuple[PortfolioMember, ...] = (),
) -> DailyDevelopmentsBrief:
    """Seçilen günün önemli piyasa gelişmelerini deterministik olarak sıralar.

    Yeni bir puan üretmez. Ana sıralama mevcut 0–100 olay önem skorudur.
    Eşit önem skorunda birincil kaynak, çoklu kaynak, portföy teması ve olay
    zamanı yalnız sıralama desteği olarak kullanılır. Fiyat yönü, AL/SAT kararı,
    teknik skor veya AI değerlendirmesi üretilmez.
    """

    if not isinstance(selected_date, date):
        raise ValueError("selected_date geçerli bir tarih olmalıdır.")
    if not isinstance(min_importance, int) or not 0 <= min_importance <= 100:
        raise ValueError("min_importance 0-100 aralığında tam sayı olmalıdır.")

    day_events = tuple(
        event
        for event in events
        if _local_date(event.occurred_at) == selected_date
        and event.importance_score >= min_importance
    )

    if portfolio_members:
        radar = build_portfolio_impact_radar(
            day_events,
            news_by_event,
            portfolio_members,
        )
        portfolio_by_event = _portfolio_hits_by_event(radar)
    else:
        portfolio_by_event = {}

    developments: list[DailyDevelopment] = []
    for event in day_events:
        event_news = tuple(news_by_event.get(event.event_id, ()))
        assessment = assess_event_impact(event, event_news)
        sector_targets: list[str] = []
        symbol_targets: list[str] = []
        direct_target_count = 0
        sensitivity_target_count = 0

        for link in assessment.links:
            if link.relation is ImpactRelation.DIRECT:
                direct_target_count += 1
            elif link.relation is ImpactRelation.SENSITIVITY:
                sensitivity_target_count += 1

            if (
                link.target_type is ImpactTargetType.SECTOR
                and link.target not in sector_targets
            ):
                sector_targets.append(link.target)
            elif (
                link.target_type is ImpactTargetType.SYMBOL
                and link.target not in symbol_targets
            ):
                symbol_targets.append(link.target)

        developments.append(
            DailyDevelopment(
                event_id=event.event_id,
                event_title=event.title,
                occurred_at=event.occurred_at,
                importance_score=event.importance_score,
                event_type=event.event_type.value,
                market_scope=event.market_scope.value,
                source_count=len(event_news),
                has_tier1_source=any(
                    item.source_tier is SourceTier.TIER_1_OFFICIAL
                    for item in event_news
                ),
                sector_targets=tuple(sector_targets),
                symbol_targets=tuple(symbol_targets),
                direct_target_count=direct_target_count,
                sensitivity_target_count=sensitivity_target_count,
                portfolio_symbols=tuple(portfolio_by_event.get(event.event_id, ())),
            )
        )

    developments.sort(
        key=lambda item: (
            -item.importance_score,
            -int(item.has_tier1_source),
            -int(item.is_multi_source),
            -int(item.has_portfolio_touch),
            -item.occurred_at.timestamp(),
            item.event_id,
        )
    )

    ordered = tuple(developments)
    return DailyDevelopmentsBrief(
        selected_date=selected_date,
        developments=ordered,
        total_event_count=len(ordered),
        high_importance_count=sum(item.is_high_importance for item in ordered),
        tier1_event_count=sum(item.has_tier1_source for item in ordered),
        multi_source_event_count=sum(item.is_multi_source for item in ordered),
        portfolio_touched_event_count=sum(item.has_portfolio_touch for item in ordered),
    )


def daily_development_rows(
    brief: DailyDevelopmentsBrief,
) -> list[dict[str, object]]:
    return [
        {
            "Saat": item.occurred_at.astimezone(ISTANBUL).strftime("%H:%M"),
            "Önem": item.importance_score,
            "Olay": item.event_title,
            "Tür": item.event_type,
            "Kapsam": item.market_scope,
            "Birincil kaynak": "Evet" if item.has_tier1_source else "Hayır",
            "Kaynak": item.source_count,
            "Sektörler": ", ".join(item.sector_targets) or "—",
            "Hisseler": ", ".join(item.symbol_targets) or "—",
            "Portföy teması": ", ".join(item.portfolio_symbols) or "—",
            "Doğrudan bağlantı": item.direct_target_count,
            "Duyarlılık": item.sensitivity_target_count,
            "Olay kimliği": item.event_id,
        }
        for item in brief.developments
    ]
