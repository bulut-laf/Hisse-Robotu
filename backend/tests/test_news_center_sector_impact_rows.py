from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.news_center.models import (
    EventType,
    ImportanceBreakdown,
    MarketEvent,
    MarketScope,
)
from backend.app.news_center.sector_impact import (
    build_sector_impact_map,
    sector_event_rows,
    sector_summary_rows,
)

TZ = ZoneInfo("Europe/Istanbul")


def _event():
    breakdown = ImportanceBreakdown(30, 24, 28, 15)
    return MarketEvent(
        event_id="e1",
        title="Enflasyon verisi",
        event_type=EventType.ENFLASYON,
        occurred_at=datetime(2026, 8, 5, 10, 0, tzinfo=TZ),
        market_scope=MarketScope.TURKEY_MACRO,
        sectors=(),
        symbols=(),
        importance_score=breakdown.total,
        importance_breakdown=breakdown,
    )


def test_sektor_ozet_satirlari_karar_destek_alanlarini_tasir():
    sector_map = build_sector_impact_map((_event(),))
    rows = sector_summary_rows(sector_map)
    assert rows
    assert {
        "Sektör",
        "Olay",
        "Önem ≥80",
        "Doğrudan",
        "Duyarlılık",
        "En yüksek önem",
        "En yüksek bağlantı güveni",
        "Son olay",
        "Etiketler",
    } <= set(rows[0])


def test_sektor_olay_satirlari_gerekceyi_gosterir():
    sector_map = build_sector_impact_map((_event(),))
    rows = sector_event_rows(sector_map)
    assert rows
    assert rows[0]["Gerekçe"]
    assert rows[0]["Bağlantı"] == "SENSITIVITY"
