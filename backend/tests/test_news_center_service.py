from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from backend.app.news_center.archive import NewsArchive
from backend.app.news_center.models import (
    EventType,
    MarketScope,
    SourceTier,
)
from backend.app.news_center.service import (
    ManualNewsRequest,
    NewsCenterService,
)


TZ = ZoneInfo("Europe/Istanbul")


def _request(*, source="TCMB", tier=SourceTier.TIER_1_OFFICIAL):
    published = datetime(2026, 8, 5, 14, 0, tzinfo=TZ)
    return ManualNewsRequest(
        source_name=source,
        source_tier=tier,
        headline="Politika faizi kararı",
        published_at=published,
        body="Para Politikası Kurulu karar metni.",
        source_reference="PPK",
        event_title="TCMB faiz kararı",
        event_type=EventType.PARA_POLITIKASI,
        occurred_at=datetime(2026, 8, 5, 13, 30, tzinfo=TZ),
        market_scope=MarketScope.TURKEY_MACRO,
        sectors=("Banka",),
        symbols=("GARAN",),
    )


def test_manual_service_yeni_olay_ve_haber_olusturur(tmp_path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = NewsCenterService(
        archive,
        now_provider=lambda: datetime(
            2026, 8, 5, 14, 5, tzinfo=timezone.utc
        ),
    )
    result = service.submit_manual(_request())

    assert result.attached_to_existing_event is False
    assert result.event.title == "TCMB faiz kararı"
    assert result.event.importance_score == 99
    assert result.event.news_ids == (result.news.news_id,)
    assert result.event.symbols == ("GARAN.IS",)


def test_manual_service_mevcut_olaya_farkli_kaynak_baglar(tmp_path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = NewsCenterService(
        archive,
        now_provider=lambda: datetime(
            2026, 8, 5, 14, 5, tzinfo=timezone.utc
        ),
    )
    first = service.submit_manual(_request())

    second_request = ManualNewsRequest(
        source_name="Reuters",
        source_tier=SourceTier.TIER_2_MAJOR_FINANCIAL,
        headline="Turkey central bank decision",
        published_at=datetime(2026, 8, 5, 14, 10, tzinfo=TZ),
        body="Reuters reports the central bank decision.",
        source_reference="Reuters",
    )
    second = service.submit_manual(
        second_request,
        existing_event_id=first.event.event_id,
    )

    assert second.attached_to_existing_event is True
    assert second.event.event_id == first.event.event_id
    assert len(second.event.news_ids) == 2


def test_hash_ayni_girdide_ayni_sonucu_verir():
    request = _request()
    assert (
        NewsCenterService.content_hash(request)
        == NewsCenterService.content_hash(request)
    )
