from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from backend.app.news_center.grouping import (
    GroupingDecision,
    best_event_match,
    evaluate_event_match,
    title_similarity,
)
from backend.app.news_center.models import (
    EventType,
    ImportanceBreakdown,
    MarketEvent,
    MarketScope,
    NewsRecord,
    SourceTier,
)


TZ = ZoneInfo("Europe/Istanbul")


def _event(
    *,
    event_id="event-1",
    title="TCMB politika faizi kararı",
    event_type=EventType.PARA_POLITIKASI,
    scope=MarketScope.TURKEY_MACRO,
    occurred=None,
    symbols=(),
):
    occurred = occurred or datetime(2026, 8, 5, 14, 0, tzinfo=TZ)
    breakdown = ImportanceBreakdown(30, 24, 30, 15)
    return MarketEvent(
        event_id=event_id,
        title=title,
        event_type=event_type,
        occurred_at=occurred,
        market_scope=scope,
        sectors=(),
        symbols=symbols,
        importance_score=breakdown.total,
        importance_breakdown=breakdown,
    )


def _news(
    *,
    event_id="event-1",
    headline="TCMB politika faizi kararını açıkladı",
    source_reference="https://example.com/ppk-20260805",
):
    stamp = datetime(2026, 8, 5, 14, 5, tzinfo=TZ)
    return NewsRecord(
        news_id=f"news-{event_id}",
        event_id=event_id,
        source_name="TCMB",
        source_tier=SourceTier.TIER_1_OFFICIAL,
        headline=headline,
        published_at=stamp,
        body="Para Politikası Kurulu karar metni.",
        source_reference=source_reference,
        content_hash=("a" * 63) + ("1" if event_id == "event-1" else "2"),
        archived_at=stamp,
    )


def test_title_similarity_turkce_karakter_ve_gereksiz_kelimeleri_normalize_eder():
    score = title_similarity(
        "TCMB politika faizi kararı açıklandı",
        "TCMB Politika Faizi Kararını Açıkladı",
    )
    assert score >= 0.75


def test_ayni_guclu_referans_auto_attach_uretir():
    event = _event()
    match = evaluate_event_match(
        requested_title="Merkez Bankası faiz kararı",
        event_type=EventType.PARA_POLITIKASI,
        market_scope=MarketScope.TURKEY_MACRO,
        occurred_at=datetime(2026, 8, 5, 15, 0, tzinfo=TZ),
        symbols=(),
        source_reference="https://example.com/ppk-20260805",
        event=event,
        attached_news=(_news(),),
    )
    assert match is not None
    assert match.decision is GroupingDecision.AUTO_ATTACH


def test_makro_ayni_gun_benzer_baslik_auto_attach_uretir():
    event = _event()
    match = evaluate_event_match(
        requested_title="TCMB politika faizi kararını açıkladı",
        event_type=EventType.PARA_POLITIKASI,
        market_scope=MarketScope.TURKEY_MACRO,
        occurred_at=datetime(2026, 8, 5, 14, 30, tzinfo=TZ),
        symbols=(),
        source_reference="Reuters-TR",
        event=event,
        attached_news=(_news(),),
    )
    assert match is not None
    assert match.decision is GroupingDecision.AUTO_ATTACH


def test_sirket_olayinda_ayni_hisse_zorunludur():
    event = _event(
        title="THYAO finansal sonuçları",
        event_type=EventType.FINANSAL_SONUCLAR,
        scope=MarketScope.COMPANY,
        symbols=("THYAO",),
    )
    match = evaluate_event_match(
        requested_title="THYAO finansal sonuçları açıklandı",
        event_type=EventType.FINANSAL_SONUCLAR,
        market_scope=MarketScope.COMPANY,
        occurred_at=datetime(2026, 8, 5, 14, 30, tzinfo=TZ),
        symbols=("ASELS.IS",),
        source_reference="",
        event=event,
        attached_news=(),
    )
    assert match is None


def test_sirket_ayni_hisse_zayif_benzerlik_review_uretir():
    event = _event(
        title="THYAO ikinci çeyrek finansal sonuçları",
        event_type=EventType.FINANSAL_SONUCLAR,
        scope=MarketScope.COMPANY,
        symbols=("THYAO",),
    )
    match = evaluate_event_match(
        requested_title="THYAO çeyrek kâr rakamları",
        event_type=EventType.FINANSAL_SONUCLAR,
        market_scope=MarketScope.COMPANY,
        occurred_at=datetime(2026, 8, 5, 22, 0, tzinfo=TZ),
        symbols=("THYAO.IS",),
        source_reference="",
        event=event,
        attached_news=(),
    )
    assert match is not None
    assert match.decision is GroupingDecision.REVIEW


def test_farkli_olay_turu_asla_gruplanmaz():
    event = _event()
    match = evaluate_event_match(
        requested_title="TCMB politika faizi kararı",
        event_type=EventType.ENFLASYON,
        market_scope=MarketScope.TURKEY_MACRO,
        occurred_at=event.occurred_at,
        symbols=(),
        source_reference="",
        event=event,
        attached_news=(_news(),),
    )
    assert match is None


def test_diger_turu_otomatik_gruplanmaz():
    event = _event(event_type=EventType.DIGER, scope=MarketScope.BIST_WIDE)
    match = evaluate_event_match(
        requested_title=event.title,
        event_type=EventType.DIGER,
        market_scope=MarketScope.BIST_WIDE,
        occurred_at=event.occurred_at,
        symbols=(),
        source_reference="",
        event=event,
        attached_news=(),
    )
    assert match is None


def test_best_match_auto_attach_adayini_review_adayina_tercih_eder():
    auto = _event(event_id="auto", occurred=datetime(2026, 8, 5, 14, 0, tzinfo=TZ))
    review = _event(
        event_id="review",
        title="TCMB faiz değerlendirmesi politika kararı",
        occurred=datetime(2026, 8, 5, 3, 0, tzinfo=TZ),
    )
    match = best_event_match(
        requested_title="TCMB politika faizi kararını açıkladı",
        event_type=EventType.PARA_POLITIKASI,
        market_scope=MarketScope.TURKEY_MACRO,
        occurred_at=datetime(2026, 8, 5, 14, 20, tzinfo=TZ),
        symbols=(),
        source_reference="",
        events=(review, auto),
        news=(),
    )
    assert match is not None
    assert match.event_id == "auto"
    assert match.decision is GroupingDecision.AUTO_ATTACH
