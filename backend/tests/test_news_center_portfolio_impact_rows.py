from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.news_center.models import (
    EventType,
    ImportanceBreakdown,
    MarketEvent,
    MarketScope,
)
from backend.app.news_center.portfolio_impact import (
    PortfolioMember,
    build_portfolio_impact_radar,
    portfolio_impact_rows,
    portfolio_symbol_summary_rows,
)

TZ = ZoneInfo("Europe/Istanbul")


def _event():
    breakdown = ImportanceBreakdown(30, 25, 20, 15)
    return MarketEvent(
        event_id="event-row",
        title="BIST geneli olay",
        event_type=EventType.REGULASYON,
        occurred_at=datetime(2026, 8, 5, 12, 0, tzinfo=TZ),
        market_scope=MarketScope.BIST_WIDE,
        sectors=(),
        symbols=("ASELS",),
        importance_score=breakdown.total,
        importance_breakdown=breakdown,
    )


def test_portfoy_etki_satirlari_gerekce_ve_eslesme_turunu_gosterir():
    radar = build_portfolio_impact_radar(
        (_event(),),
        {},
        (PortfolioMember("ASELS", "Savunma"),),
    )
    rows = portfolio_impact_rows(radar)
    assert rows[0]["Hisse"] == "ASELS.IS"
    assert rows[0]["Eşleşme"] == "DIRECT_SYMBOL"
    assert rows[0]["Gerekçe"]


def test_portfoy_ozet_satiri_olay_sayisini_sismez():
    event = _event()
    radar = build_portfolio_impact_radar(
        (event,),
        {},
        (PortfolioMember("ASELS", "Savunma"),),
    )
    rows = portfolio_symbol_summary_rows(radar)
    assert rows == [
        {
            "Hisse": "ASELS.IS",
            "Sektör": "Savunma",
            "Olay sayısı": 1,
            "En güçlü eşleşme": "DIRECT_SYMBOL",
            "Maks. olay önemi": 90,
            "Maks. bağlantı güveni": 100,
        }
    ]


def test_etkisiz_portfoy_icin_ozet_bos_doner():
    event = MarketEvent(
        event_id="unrelated",
        title="Başka şirket",
        event_type=EventType.KAP_ACIKLAMASI,
        occurred_at=datetime(2026, 8, 5, 12, 0, tzinfo=TZ),
        market_scope=MarketScope.COMPANY,
        sectors=(),
        symbols=("THYAO",),
        importance_score=60,
        importance_breakdown=ImportanceBreakdown(20, 10, 20, 10),
    )
    radar = build_portfolio_impact_radar(
        (event,),
        {},
        (PortfolioMember("ASELS", "Savunma"),),
    )
    assert portfolio_symbol_summary_rows(radar) == []
