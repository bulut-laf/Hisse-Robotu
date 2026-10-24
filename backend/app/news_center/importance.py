from __future__ import annotations

from datetime import datetime

from .models import (
    EventType,
    ImportanceBreakdown,
    MarketScope,
    SourceTier,
)


SOURCE_SCORES: dict[SourceTier, int] = {
    SourceTier.TIER_1_OFFICIAL: 30,
    SourceTier.TIER_2_MAJOR_FINANCIAL: 24,
    SourceTier.OTHER_VERIFIED: 16,
    SourceTier.MANUAL: 8,
}

SCOPE_SCORES: dict[MarketScope, int] = {
    MarketScope.GLOBAL: 25,
    MarketScope.TURKEY_MACRO: 24,
    MarketScope.BIST_WIDE: 22,
    MarketScope.SECTOR: 16,
    MarketScope.COMPANY: 12,
    MarketScope.OTHER: 6,
}

EVENT_SCORES: dict[EventType, int] = {
    EventType.PARA_POLITIKASI: 30,
    EventType.ENFLASYON: 28,
    EventType.BUYUME: 24,
    EventType.ISTIHDAM: 22,
    EventType.FAIZ: 28,
    EventType.DOVIZ: 23,
    EventType.EMTIA: 18,
    EventType.REGULASYON: 27,
    EventType.KAP_ACIKLAMASI: 20,
    EventType.FINANSAL_SONUCLAR: 22,
    EventType.TEMETTU: 14,
    EventType.SERMAYE_ISLEMI: 22,
    EventType.BORCLANMA_FINANSMAN: 18,
    EventType.SEKTOR: 18,
    EventType.JEOPOLITIK: 26,
    EventType.DIGER: 10,
}


def _time_sensitivity_score(
    *,
    occurred_at: datetime,
    published_at: datetime,
) -> int:
    if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
        raise ValueError("Olay zamanı saat dilimi içermelidir.")
    if published_at.tzinfo is None or published_at.utcoffset() is None:
        raise ValueError("Yayın zamanı saat dilimi içermelidir.")

    delay_seconds = max(
        0.0,
        (published_at - occurred_at).total_seconds(),
    )
    if delay_seconds <= 60 * 60:
        return 15
    if delay_seconds <= 6 * 60 * 60:
        return 12
    if delay_seconds <= 24 * 60 * 60:
        return 9
    if delay_seconds <= 72 * 60 * 60:
        return 6
    return 3


def calculate_importance(
    *,
    source_tier: SourceTier,
    market_scope: MarketScope,
    event_type: EventType,
    occurred_at: datetime,
    published_at: datetime,
) -> ImportanceBreakdown:
    """
    Deterministik 0-100 önem bileşenlerini üretir.

    Skor yalnız kayıtlı kaynak seviyesi, piyasa kapsamı, olay türü ve
    olay-yayın zaman farkından hesaplanır. AI veya teknik analiz sonucu
    bu skora girmez.
    """

    source_tier = SourceTier(source_tier)
    market_scope = MarketScope(market_scope)
    event_type = EventType(event_type)

    return ImportanceBreakdown(
        source_reliability=SOURCE_SCORES[source_tier],
        market_scope=SCOPE_SCORES[market_scope],
        event_significance=EVENT_SCORES[event_type],
        time_sensitivity=_time_sensitivity_score(
            occurred_at=occurred_at,
            published_at=published_at,
        ),
    )
