from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from backend.app.news_center.daily_developments import (
    build_daily_developments_brief,
    daily_development_rows,
)
from backend.app.news_center.models import (
    EventType,
    ImportanceBreakdown,
    MarketEvent,
    MarketScope,
    NewsRecord,
    SourceTier,
)
from backend.app.news_center.portfolio_impact import PortfolioMember


ISTANBUL = ZoneInfo("Europe/Istanbul")


def _event(event_id, title, occurred_at, importance, *, symbols=(), sectors=()):
    breakdown = ImportanceBreakdown(30, 25, 30, importance - 85) if importance >= 88 else ImportanceBreakdown(24, 22, 22, importance - 68)
    return MarketEvent(
        event_id=event_id,
        title=title,
        event_type=EventType.KAP_ACIKLAMASI if symbols else EventType.FAIZ,
        occurred_at=occurred_at,
        market_scope=MarketScope.COMPANY if symbols else MarketScope.TURKEY_MACRO,
        sectors=sectors,
        symbols=symbols,
        importance_score=importance,
        importance_breakdown=breakdown,
    )


def _news(event_id, news_id, tier=SourceTier.TIER_1_OFFICIAL):
    stamp = datetime(2026, 8, 5, 10, 0, tzinfo=ISTANBUL)
    return NewsRecord(
        news_id=news_id,
        event_id=event_id,
        source_name="KAP" if tier is SourceTier.TIER_1_OFFICIAL else "Reuters",
        source_tier=tier,
        headline="Başlık",
        published_at=stamp,
        body="Açıklama metni.",
        source_reference="ref",
        content_hash=(news_id[0] if news_id else "a") * 64,
        archived_at=stamp,
    )


def test_istanbul_tarihine_gore_filtreler():
    # UTC'de 4 Ağustos, İstanbul'da 5 Ağustos.
    event = _event(
        "e1",
        "Gece olayı",
        datetime(2026, 8, 4, 22, 30, tzinfo=timezone.utc),
        75,
    )
    brief = build_daily_developments_brief(
        (event,),
        {"e1": (_news("e1", "a1"),)},
        selected_date=date(2026, 8, 5),
        min_importance=70,
    )
    assert brief.total_event_count == 1


def test_onem_esigi_altindaki_olayi_gostermez():
    event = _event(
        "e1",
        "Düşük önem",
        datetime(2026, 8, 5, 10, 0, tzinfo=ISTANBUL),
        70,
    )
    brief = build_daily_developments_brief(
        (event,),
        {"e1": (_news("e1", "a1"),)},
        selected_date=date(2026, 8, 5),
        min_importance=80,
    )
    assert brief.total_event_count == 0


def test_ana_siralama_mevcut_onem_skorudur():
    high = _event("e1", "Yüksek", datetime(2026, 8, 5, 9, 0, tzinfo=ISTANBUL), 90)
    low = _event("e2", "Daha düşük", datetime(2026, 8, 5, 11, 0, tzinfo=ISTANBUL), 75)
    brief = build_daily_developments_brief(
        (low, high),
        {
            "e1": (_news("e1", "a1", SourceTier.TIER_2_MAJOR_FINANCIAL),),
            "e2": (_news("e2", "b1"), _news("e2", "c1")),
        },
        selected_date=date(2026, 8, 5),
        min_importance=0,
    )
    assert [item.event_id for item in brief.developments] == ["e1", "e2"]


def test_esit_onemde_birincil_kaynak_siralama_destegidir():
    a = _event("e1", "Resmî", datetime(2026, 8, 5, 9, 0, tzinfo=ISTANBUL), 75)
    b = _event("e2", "İkincil", datetime(2026, 8, 5, 11, 0, tzinfo=ISTANBUL), 75)
    brief = build_daily_developments_brief(
        (b, a),
        {
            "e1": (_news("e1", "a1", SourceTier.TIER_1_OFFICIAL),),
            "e2": (_news("e2", "b1", SourceTier.TIER_2_MAJOR_FINANCIAL),),
        },
        selected_date=date(2026, 8, 5),
        min_importance=0,
    )
    assert brief.developments[0].event_id == "e1"


def test_portfoy_temasi_yeni_puan_uretmeden_gosterilir():
    event = _event(
        "e1",
        "THYAO açıklaması",
        datetime(2026, 8, 5, 10, 0, tzinfo=ISTANBUL),
        75,
        symbols=("THYAO",),
        sectors=("Ulaştırma",),
    )
    brief = build_daily_developments_brief(
        (event,),
        {"e1": (_news("e1", "a1"),)},
        selected_date=date(2026, 8, 5),
        min_importance=0,
        portfolio_members=(PortfolioMember("THYAO", "Ulaştırma"),),
    )
    item = brief.developments[0]
    assert item.portfolio_symbols == ("THYAO.IS",)
    assert item.importance_score == 75
    assert brief.portfolio_touched_event_count == 1


def test_satirlar_birincil_ve_portfoy_bilgisi_tasir():
    event = _event(
        "e1",
        "THYAO açıklaması",
        datetime(2026, 8, 5, 10, 0, tzinfo=ISTANBUL),
        75,
        symbols=("THYAO",),
    )
    brief = build_daily_developments_brief(
        (event,),
        {"e1": (_news("e1", "a1"),)},
        selected_date=date(2026, 8, 5),
        min_importance=0,
        portfolio_members=(PortfolioMember("THYAO"),),
    )
    rows = daily_development_rows(brief)
    assert rows[0]["Birincil kaynak"] == "Evet"
    assert rows[0]["Portföy teması"] == "THYAO.IS"
