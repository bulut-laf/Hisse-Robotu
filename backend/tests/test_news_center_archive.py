from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.archive import (
    DuplicateNewsError,
    NewsArchive,
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


def _event():
    breakdown = ImportanceBreakdown(30, 12, 20, 15)
    return MarketEvent(
        event_id="event-1",
        title="THYAO açıklaması",
        event_type=EventType.KAP_ACIKLAMASI,
        occurred_at=datetime(2026, 8, 5, 10, 0, tzinfo=TZ),
        market_scope=MarketScope.COMPANY,
        sectors=("Ulaştırma",),
        symbols=("THYAO",),
        importance_score=breakdown.total,
        importance_breakdown=breakdown,
    )


def _news(news_id="news-1", content_hash="a" * 64, source="KAP"):
    stamp = datetime(2026, 8, 5, 10, 10, tzinfo=TZ)
    return NewsRecord(
        news_id=news_id,
        event_id="event-1",
        source_name=source,
        source_tier=SourceTier.TIER_1_OFFICIAL,
        headline="THYAO açıklaması",
        published_at=stamp,
        body="Şirket yeni bir açıklama yayımladı.",
        source_reference="KAP-123",
        content_hash=content_hash,
        archived_at=stamp,
    )


def test_sqlite_arsivi_kalici_olay_ve_haber_saklar(tmp_path):
    path = tmp_path / "news.sqlite3"
    archive = NewsArchive(path)
    archive.archive_new_event(
        _event(),
        _news(),
        created_at=datetime(2026, 8, 5, 10, 11, tzinfo=TZ),
    )

    reopened = NewsArchive(path)
    events = reopened.list_events()
    news = reopened.list_news()

    assert len(events) == 1
    assert events[0].news_ids == ("news-1",)
    assert events[0].symbols == ("THYAO.IS",)
    assert len(news) == 1
    assert news[0].source_name == "KAP"


def test_birebir_duplicate_content_hash_reddedilir(tmp_path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    archive.archive_new_event(
        _event(),
        _news(),
        created_at=datetime(2026, 8, 5, 10, 11, tzinfo=TZ),
    )

    with pytest.raises(DuplicateNewsError):
        archive.attach_news(
            "event-1",
            _news(news_id="news-2"),
        )


def test_ayni_olaya_ikinci_kaynak_baglanabilir(tmp_path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    archive.archive_new_event(
        _event(),
        _news(),
        created_at=datetime(2026, 8, 5, 10, 11, tzinfo=TZ),
    )
    event = archive.attach_news(
        "event-1",
        _news(
            news_id="news-2",
            content_hash="b" * 64,
            source="Reuters",
        ),
    )
    assert event.news_ids == ("news-1", "news-2")
