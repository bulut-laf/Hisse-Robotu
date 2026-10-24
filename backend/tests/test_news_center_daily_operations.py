from datetime import date, datetime, timedelta, timezone

import pytest

from backend.app.news_center.daily_operations import (
    build_daily_news_operations_brief,
    daily_operations_event_rows,
    daily_operations_source_rows,
)
from backend.app.news_center.models import (
    EventType,
    ImportanceBreakdown,
    MarketEvent,
    MarketScope,
    NewsRecord,
    SourceTier,
)
from backend.app.news_center.official_source_operations import (
    OfficialSourceOperationKind,
    OfficialSourceOperationRecord,
)


DAY = date(2026, 8, 5)
T0 = datetime(2026, 8, 5, 8, 0, tzinfo=timezone.utc)
AS_OF = datetime(2026, 8, 5, 20, 0, tzinfo=timezone.utc)
SOURCES = ("KAP", "TCMB", "TÜİK")


def breakdown(total):
    remaining = total
    parts = []
    for maximum in (30, 25, 30, 15):
        value = min(maximum, remaining)
        parts.append(value)
        remaining -= value
    assert remaining == 0
    return ImportanceBreakdown(*parts)


def event(
    event_id,
    *,
    at=T0,
    importance=80,
    event_type=EventType.DIGER,
    symbols=(),
    sectors=(),
    news_ids=(),
):
    return MarketEvent(
        event_id=event_id,
        title=f"Olay {event_id}",
        event_type=event_type,
        occurred_at=at,
        market_scope=MarketScope.OTHER,
        sectors=sectors,
        symbols=symbols,
        importance_score=importance,
        importance_breakdown=breakdown(importance),
        news_ids=news_ids,
    )


def news(
    news_id,
    event_id,
    *,
    at=T0,
    source="KAP",
    tier=SourceTier.TIER_1_OFFICIAL,
):
    return NewsRecord(
        news_id=news_id,
        event_id=event_id,
        source_name=source,
        source_tier=tier,
        headline=f"Haber {news_id}",
        published_at=at,
        body="İçerik",
        source_reference="https://example.test/x",
        content_hash=("a" if news_id == "n1" else "b") * 64,
        archived_at=at,
    )


def operation(operation_id, source, kind, *, at=T0):
    return OfficialSourceOperationRecord(
        operation_id=operation_id,
        source_name=source,
        kind=kind,
        occurred_at=at,
        source_reference="https://example.test/x",
        detail="",
    )


def test_bos_gun_bos_brief():
    brief = build_daily_news_operations_brief((), (), (), selected_date=DAY, official_source_names=SOURCES, as_of=AS_OF)
    assert brief.event_count == 0
    assert brief.news_count == 0
    assert brief.official_sources_used_count == 0
    assert len(brief.official_sources) == 3


def test_gun_disindaki_kayitlar_haric():
    tomorrow = T0 + timedelta(days=1)
    brief = build_daily_news_operations_brief((event("e1", at=tomorrow),), (news("n1", "e1", at=tomorrow),), (), selected_date=DAY, official_source_names=SOURCES, as_of=AS_OF + timedelta(days=1))
    assert brief.event_count == 0
    assert brief.news_count == 0


def test_future_kayitlar_haric():
    future = datetime(2026, 8, 5, 21, 0, tzinfo=timezone.utc)
    brief = build_daily_news_operations_brief((event("e1", at=future),), (news("n1", "e1", at=future),), (), selected_date=DAY, official_source_names=SOURCES, as_of=AS_OF)
    assert brief.event_count == 0
    assert brief.news_count == 0


def test_temel_metrikler():
    events = (
        event("e1", importance=90, event_type=EventType.KAP_ACIKLAMASI, symbols=("THYAO",), news_ids=("n1",)),
        event("e2", importance=70, symbols=("ASELS",), news_ids=("n2",)),
    )
    news_items = (
        news("n1", "e1", source="KAP"),
        news("n2", "e2", source="Reuters", tier=SourceTier.TIER_2_MAJOR_FINANCIAL),
    )
    brief = build_daily_news_operations_brief(events, news_items, (), selected_date=DAY, official_source_names=SOURCES, portfolio_symbols=("THYAO",), as_of=AS_OF)
    assert brief.event_count == 2
    assert brief.news_count == 2
    assert brief.high_importance_event_count == 1
    assert brief.tier1_news_count == 1
    assert brief.kap_event_count == 1
    assert brief.unique_symbol_count == 2
    assert brief.portfolio_touched_symbols == ("THYAO.IS",)


def test_priority_importance_sirasina_gore():
    events = (event("low", importance=60), event("high", importance=95), event("mid", importance=80))
    brief = build_daily_news_operations_brief(events, (), (), selected_date=DAY, official_source_names=SOURCES, as_of=AS_OF)
    assert [item.event_id for item in brief.priority_events] == ["high", "mid", "low"]


def test_priority_limit():
    events = tuple(event(f"e{i}", importance=80) for i in range(12))
    brief = build_daily_news_operations_brief(events, (), (), selected_date=DAY, official_source_names=SOURCES, as_of=AS_OF, priority_limit=5)
    assert len(brief.priority_events) == 5


@pytest.mark.parametrize("priority_limit", (0, 51))
def test_priority_limit_siniri(priority_limit):
    with pytest.raises(ValueError, match="priority_limit"):
        build_daily_news_operations_brief((), (), (), selected_date=DAY, official_source_names=SOURCES, as_of=AS_OF, priority_limit=priority_limit)


def test_source_operasyon_metrikleri():
    ops = (
        operation("o1", "KAP", OfficialSourceOperationKind.PREVIEW_SUCCESS),
        operation("o2", "KAP", OfficialSourceOperationKind.ARCHIVE_SUCCESS),
        operation("o3", "TCMB", OfficialSourceOperationKind.PREVIEW_ERROR),
        operation("o4", "TÜİK", OfficialSourceOperationKind.PREVIEW_BLOCKED),
    )
    brief = build_daily_news_operations_brief((), (), ops, selected_date=DAY, official_source_names=SOURCES, as_of=AS_OF)
    assert brief.source_operation_count == 4
    assert brief.source_operation_error_count == 1
    assert brief.official_sources_used_count == 3
    kap = brief.official_sources[0]
    assert kap.preview_success_count == 1
    assert kap.archive_success_count == 1
    assert kap.last_success_at == T0
    assert brief.official_sources[1].preview_error_count == 1
    assert brief.official_sources[2].preview_blocked_count == 1
    assert brief.official_sources[2].last_success_at is None


def test_official_source_news_kullanim_sayilir():
    brief = build_daily_news_operations_brief((event("e1"),), (news("n1", "e1", source="KAP"),), (), selected_date=DAY, official_source_names=SOURCES, as_of=AS_OF)
    assert brief.official_sources_used_count == 1
    assert brief.official_sources[0].news_count == 1


def test_latest_news():
    n1 = news("n1", "e1", at=T0)
    n2 = news("n2", "e2", at=T0 + timedelta(hours=2), source="TCMB")
    brief = build_daily_news_operations_brief((), (n1, n2), (), selected_date=DAY, official_source_names=SOURCES, as_of=AS_OF)
    assert brief.latest_news_published_at == n2.published_at


def test_latest_source_success_erroru_saymaz():
    ops = (
        operation("o1", "KAP", OfficialSourceOperationKind.PREVIEW_SUCCESS),
        operation("o2", "KAP", OfficialSourceOperationKind.PREVIEW_ERROR, at=T0 + timedelta(hours=1)),
    )
    brief = build_daily_news_operations_brief((), (), ops, selected_date=DAY, official_source_names=SOURCES, as_of=AS_OF)
    assert brief.latest_source_success_at == T0


def test_event_news_sayilari():
    ev = event("e1", news_ids=("n1", "n2"))
    news_items = (
        news("n1", "e1"),
        news("n2", "e1", source="Reuters", tier=SourceTier.TIER_2_MAJOR_FINANCIAL),
    )
    brief = build_daily_news_operations_brief((ev,), news_items, (), selected_date=DAY, official_source_names=SOURCES, as_of=AS_OF)
    row = brief.priority_events[0]
    assert row.news_count == 2
    assert row.tier1_news_count == 1


def test_event_rows_formati():
    brief = build_daily_news_operations_brief((event("e1", symbols=("THYAO",), sectors=("Havacılık",)),), (), (), selected_date=DAY, official_source_names=SOURCES, as_of=AS_OF)
    rows = daily_operations_event_rows(brief)
    assert rows[0]["Önem"] == 80
    assert rows[0]["Hisseler"] == "THYAO.IS"
    assert rows[0]["Sektörler"] == "Havacılık"


def test_source_rows_formati():
    brief = build_daily_news_operations_brief((), (), (), selected_date=DAY, official_source_names=SOURCES, as_of=AS_OF)
    rows = daily_operations_source_rows(brief)
    assert rows[0]["Kaynak"] == "KAP"
    assert rows[0]["Son başarılı kullanım"] == "—"


def test_as_of_naive_reddedilir():
    with pytest.raises(ValueError, match="as_of"):
        build_daily_news_operations_brief((), (), (), selected_date=DAY, official_source_names=SOURCES, as_of=datetime(2026, 8, 5, 12, 0))


def test_source_sirasi_korunur():
    brief = build_daily_news_operations_brief((), (), (), selected_date=DAY, official_source_names=("TCMB", "KAP", "TCMB"), as_of=AS_OF)
    assert [item.source_name for item in brief.official_sources] == ["TCMB", "KAP"]


def test_portfoy_temas_sirali_benzersiz():
    brief = build_daily_news_operations_brief((event("e1", symbols=("THYAO", "ASELS")), event("e2", symbols=("ASELS",))), (), (), selected_date=DAY, official_source_names=SOURCES, portfolio_symbols=("THYAO", "ASELS"), as_of=AS_OF)
    assert brief.portfolio_touched_symbols == ("ASELS.IS", "THYAO.IS")
