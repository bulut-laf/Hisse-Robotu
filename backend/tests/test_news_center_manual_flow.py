from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.archive import DuplicateNewsError, NewsArchive
from backend.app.news_center.models import EventType, MarketScope, SourceTier
from backend.app.news_center.service import ManualNewsRequest, NewsCenterService


TZ = ZoneInfo("Europe/Istanbul")
NOW = datetime(2026, 8, 5, 14, 30, tzinfo=timezone.utc)


def _service(tmp_path):
    return NewsCenterService(
        NewsArchive(tmp_path / "news.sqlite3"),
        now_provider=lambda: NOW,
    )


def _official_request():
    return ManualNewsRequest(
        source_name="TCMB",
        source_tier=SourceTier.TIER_1_OFFICIAL,
        headline="Politika faizi kararı",
        published_at=datetime(2026, 8, 5, 14, 0, tzinfo=TZ),
        body="Para Politikası Kurulu karar metni.",
        source_reference="PPK-2026-08",
        event_title="TCMB faiz kararı",
        event_type=EventType.PARA_POLITIKASI,
        occurred_at=datetime(2026, 8, 5, 13, 30, tzinfo=TZ),
        market_scope=MarketScope.TURKEY_MACRO,
        sectors=("Banka",),
        symbols=("GARAN",),
    )


def test_manuel_akis_yeni_olay_ikinci_kaynak_ve_persistence(tmp_path):
    service = _service(tmp_path)
    first = service.submit_manual(_official_request())

    second = service.submit_manual(
        ManualNewsRequest(
            source_name="Reuters",
            source_tier=SourceTier.TIER_2_MAJOR_FINANCIAL,
            headline="Turkey central bank decision",
            published_at=datetime(2026, 8, 5, 14, 10, tzinfo=TZ),
            body="Reuters reports the central bank decision.",
            source_reference="RTRS-1",
        ),
        existing_event_id=first.event.event_id,
    )

    reopened = NewsArchive(tmp_path / "news.sqlite3")
    event = reopened.get_event(first.event.event_id)
    attached = reopened.list_news_for_event(first.event.event_id)

    assert second.attached_to_existing_event is True
    assert event.news_ids == tuple(item.news_id for item in attached)
    assert [item.source_name for item in attached] == ["TCMB", "Reuters"]
    assert event.symbols == ("GARAN.IS",)


def test_list_news_for_event_baska_olayin_haberini_getirmez(tmp_path):
    service = _service(tmp_path)
    first = service.submit_manual(_official_request())
    other = service.submit_manual(
        ManualNewsRequest(
            source_name="KAP",
            source_tier=SourceTier.TIER_1_OFFICIAL,
            headline="Şirket açıklaması",
            published_at=datetime(2026, 8, 5, 15, 0, tzinfo=TZ),
            body="Şirket özel durum açıklaması yayımladı.",
            event_type=EventType.KAP_ACIKLAMASI,
            market_scope=MarketScope.COMPANY,
            symbols=("THYAO",),
        )
    )

    attached = service.archive.list_news_for_event(first.event.event_id)
    assert len(attached) == 1
    assert attached[0].event_id == first.event.event_id
    assert attached[0].event_id != other.event.event_id


def test_list_news_for_event_bos_event_id_reddeder(tmp_path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    with pytest.raises(ValueError, match="event_id boş"):
        archive.list_news_for_event("  ")


def test_duplicate_ayni_olaya_baglanirken_de_reddedilir(tmp_path):
    service = _service(tmp_path)
    first = service.submit_manual(_official_request())

    with pytest.raises(DuplicateNewsError):
        service.submit_manual(
            _official_request(),
            existing_event_id=first.event.event_id,
        )


def test_daha_guvenilir_ikinci_kaynak_olay_onemini_yukseltebilir(tmp_path):
    service = _service(tmp_path)
    first = service.submit_manual(
        ManualNewsRequest(
            source_name="Yerel Finans",
            source_tier=SourceTier.OTHER_VERIFIED,
            headline="Faiz kararı bekleniyor",
            published_at=datetime(2026, 8, 5, 14, 0, tzinfo=TZ),
            body="Faiz kararına ilişkin doğrulanmış haber.",
            event_title="TCMB faiz kararı",
            event_type=EventType.PARA_POLITIKASI,
            occurred_at=datetime(2026, 8, 5, 13, 30, tzinfo=TZ),
            market_scope=MarketScope.TURKEY_MACRO,
        )
    )
    before = first.event.importance_score

    second = service.submit_manual(
        ManualNewsRequest(
            source_name="TCMB",
            source_tier=SourceTier.TIER_1_OFFICIAL,
            headline="Politika faizi kararı açıklandı",
            published_at=datetime(2026, 8, 5, 14, 5, tzinfo=TZ),
            body="Para Politikası Kurulu resmî karar metni.",
        ),
        existing_event_id=first.event.event_id,
    )

    assert second.event.importance_score > before
    assert second.event.importance_breakdown.source_reliability == 30
