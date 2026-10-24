from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.archive import NewsArchive
from backend.app.news_center.grouping import GroupingDecision
from backend.app.news_center.models import EventType, MarketScope, SourceTier
from backend.app.news_center.service import (
    EventGroupingReviewRequired,
    ManualNewsRequest,
    NewsCenterService,
)


TZ = ZoneInfo("Europe/Istanbul")
NOW = datetime(2026, 8, 5, 15, 0, tzinfo=timezone.utc)


def _macro_request(*, source, headline, occurred_hour=14, reference=""):
    return ManualNewsRequest(
        source_name=source,
        source_tier=(
            SourceTier.TIER_1_OFFICIAL
            if source == "TCMB"
            else SourceTier.TIER_2_MAJOR_FINANCIAL
        ),
        headline=headline,
        published_at=datetime(2026, 8, 5, occurred_hour, 10, tzinfo=TZ),
        body=f"{headline}. Para Politikası Kurulu kararı hakkında haber.",
        source_reference=reference,
        event_title=headline,
        event_type=EventType.PARA_POLITIKASI,
        occurred_at=datetime(2026, 8, 5, occurred_hour, 0, tzinfo=TZ),
        market_scope=MarketScope.TURKEY_MACRO,
    )


def _company_request(*, source, headline, hour, body):
    return ManualNewsRequest(
        source_name=source,
        source_tier=SourceTier.TIER_1_OFFICIAL,
        headline=headline,
        published_at=datetime(2026, 8, 5, hour, 10, tzinfo=TZ),
        body=body,
        event_title=headline,
        event_type=EventType.FINANSAL_SONUCLAR,
        occurred_at=datetime(2026, 8, 5, hour, 0, tzinfo=TZ),
        market_scope=MarketScope.COMPANY,
        symbols=("THYAO",),
    )


def test_service_guclu_eslesmede_ikinci_haberi_otomatik_baglar(tmp_path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = NewsCenterService(archive, now_provider=lambda: NOW)
    first = service.submit_manual(
        _macro_request(
            source="TCMB",
            headline="TCMB politika faizi kararı",
        )
    )
    second = service.submit_manual(
        _macro_request(
            source="Reuters",
            headline="TCMB politika faizi kararını açıkladı",
        ),
        auto_group=True,
    )

    assert second.attached_to_existing_event is True
    assert second.grouped_automatically is True
    assert second.event.event_id == first.event.event_id
    assert len(archive.list_events()) == 1
    assert len(archive.list_news_for_event(first.event.event_id)) == 2
    assert second.grouping_reasons


def test_service_review_esiginde_kaydi_yazmadan_kullanici_karari_ister(tmp_path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = NewsCenterService(archive, now_provider=lambda: NOW)
    first = service.submit_manual(
        _company_request(
            source="KAP",
            headline="THYAO ikinci çeyrek finansal sonuçları",
            hour=10,
            body="THYAO ikinci çeyrek finansal sonuçlarını açıkladı.",
        )
    )

    with pytest.raises(EventGroupingReviewRequired) as captured:
        service.submit_manual(
            _company_request(
                source="KAP",
                headline="THYAO çeyrek kâr rakamları",
                hour=18,
                body="THYAO dönem kâr rakamları yayımlandı.",
            ),
            auto_group=True,
        )

    assert captured.value.match.decision is GroupingDecision.REVIEW
    assert captured.value.match.event_id == first.event.event_id
    assert len(archive.list_events()) == 1
    assert len(archive.list_news()) == 1


def test_auto_group_kapatilirsa_kullanici_ayri_olay_olusturabilir(tmp_path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = NewsCenterService(archive, now_provider=lambda: NOW)
    service.submit_manual(
        _macro_request(source="TCMB", headline="TCMB politika faizi kararı")
    )
    second = service.submit_manual(
        _macro_request(
            source="Reuters",
            headline="TCMB politika faizi kararını açıkladı",
        ),
        auto_group=False,
    )
    assert second.attached_to_existing_event is False
    assert len(archive.list_events()) == 2


def test_explicit_event_secimi_otomatik_eslestirmeden_once_gelir(tmp_path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = NewsCenterService(archive, now_provider=lambda: NOW)
    first = service.submit_manual(
        _macro_request(source="TCMB", headline="TCMB politika faizi kararı")
    )
    second = service.submit_manual(
        _macro_request(
            source="Reuters",
            headline="Farklı başlık fakat kullanıcı aynı olayı seçti",
        ),
        existing_event_id=first.event.event_id,
        auto_group=True,
    )
    assert second.attached_to_existing_event is True
    assert second.grouped_automatically is False
    assert second.event.event_id == first.event.event_id
