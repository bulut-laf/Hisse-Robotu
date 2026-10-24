from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.models import (
    EventType,
    ImportanceBreakdown,
    MarketEvent,
    MarketScope,
    NewsCenterModelError,
)


TZ = ZoneInfo("Europe/Istanbul")


def test_market_event_sembolleri_normalize_edilir():
    breakdown = ImportanceBreakdown(30, 12, 20, 15)
    event = MarketEvent(
        event_id="evt-1",
        title="  Şirket açıklaması  ",
        event_type=EventType.KAP_ACIKLAMASI,
        occurred_at=datetime(2026, 8, 5, 10, 0, tzinfo=TZ),
        market_scope=MarketScope.COMPANY,
        sectors=(" Ulaştırma ", "ulaştırma"),
        symbols=("thyao", "THYAO.IS"),
        importance_score=breakdown.total,
        importance_breakdown=breakdown,
    )
    assert event.title == "Şirket açıklaması"
    assert event.symbols == ("THYAO.IS",)
    assert event.sectors == ("Ulaştırma",)


def test_importance_score_bilesenlerle_eslesmelidir():
    breakdown = ImportanceBreakdown(30, 24, 28, 15)
    with pytest.raises(NewsCenterModelError, match="eşleşmelidir"):
        MarketEvent(
            event_id="evt-1",
            title="Enflasyon",
            event_type=EventType.ENFLASYON,
            occurred_at=datetime(2026, 8, 5, 10, 0, tzinfo=TZ),
            market_scope=MarketScope.TURKEY_MACRO,
            sectors=(),
            symbols=(),
            importance_score=1,
            importance_breakdown=breakdown,
        )


def test_naive_datetime_reddedilir():
    breakdown = ImportanceBreakdown(30, 24, 28, 15)
    with pytest.raises(NewsCenterModelError, match="saat dilimi"):
        MarketEvent(
            event_id="evt-1",
            title="Enflasyon",
            event_type=EventType.ENFLASYON,
            occurred_at=datetime(2026, 8, 5, 10, 0),
            market_scope=MarketScope.TURKEY_MACRO,
            sectors=(),
            symbols=(),
            importance_score=breakdown.total,
            importance_breakdown=breakdown,
        )
