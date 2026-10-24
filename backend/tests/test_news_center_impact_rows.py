from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.news_center.impact import assess_event_impact, impact_rows
from backend.app.news_center.models import EventType, ImportanceBreakdown, MarketEvent, MarketScope

TZ = ZoneInfo("Europe/Istanbul")


def test_impact_rows_aciklanabilir_sutunlari_tasir():
    breakdown = ImportanceBreakdown(30, 24, 30, 15)
    event = MarketEvent(
        event_id="event-1",
        title="TCMB faiz kararı",
        event_type=EventType.PARA_POLITIKASI,
        occurred_at=datetime(2026, 8, 5, 14, 0, tzinfo=TZ),
        market_scope=MarketScope.TURKEY_MACRO,
        sectors=(),
        symbols=(),
        importance_score=breakdown.total,
        importance_breakdown=breakdown,
    )
    rows = impact_rows(event, assess_event_impact(event))
    assert rows
    assert {"Hedef türü", "Hedef", "Bağlantı", "Bağlantı güveni", "Etiketler", "Gerekçe"} <= set(rows[0])
    assert all(row["Gerekçe"] for row in rows)
