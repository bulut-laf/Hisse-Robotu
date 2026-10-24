from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.app.news_center.archive import NewsArchive
from backend.app.news_center.feed_ingestion import (
    FeedIngestionError,
    FeedIngestionService,
    FeedItem,
    feed_source_statuses,
)
from backend.app.news_center.models import EventType, MarketScope, SourceTier


NOW = datetime(2026, 8, 5, 18, 0, tzinfo=timezone.utc)


def service(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    return FeedIngestionService(archive, now_provider=lambda: NOW), archive


def item(**kwargs):
    data = dict(
        source_name="Reuters",
        headline="Piyasa haberi",
        published_at=NOW,
        body="Açıklama metni",
        source_reference="https://www.reuters.com/markets/example",
    )
    data.update(kwargs)
    return FeedItem(**data)


def test_statuslar_kayitli_kaynaklardan_gelir():
    statuses = feed_source_statuses()
    names = {row.canonical_name for row in statuses}
    assert "KAP" in names
    assert "TCMB" in names
    assert "Reuters" in names


def test_sprint165te_adapterlerin_hepsi_kapali():
    assert all(row.adapter_enabled is False for row in feed_source_statuses())


def test_preview_guvenilir_kaynagi_kanoniklestirir(tmp_path):
    svc, _ = service(tmp_path)
    preview = svc.preview(item(source_name="reuters", source_reference=""))
    assert preview.source.canonical_name == "Reuters"
    assert preview.source.tier is SourceTier.TIER_2_MAJOR_FINANCIAL


def test_domain_ile_kap_dogrulanir(tmp_path):
    svc, _ = service(tmp_path)
    preview = svc.preview(item(
        source_name="Bilinmeyen",
        source_reference="https://www.kap.org.tr/tr/Bildirim/123",
    ))
    assert preview.source.canonical_name == "KAP"
    assert preview.source.tier is SourceTier.TIER_1_OFFICIAL


def test_guvenilmeyen_kaynak_reddedilir(tmp_path):
    svc, _ = service(tmp_path)
    with pytest.raises(FeedIngestionError, match="doğrulanamadı"):
        svc.preview(item(
            source_name="Rastgele Site",
            source_reference="https://example.invalid/a",
        ))


def test_preview_yazma_yapmaz(tmp_path):
    svc, archive = service(tmp_path)
    preview = svc.preview(item())
    assert preview.duplicate is False
    assert archive.list_news() == ()
    assert archive.list_events() == ()


def test_import_acik_cagriyla_arsivler(tmp_path):
    svc, archive = service(tmp_path)
    result = svc.import_item(item())
    assert result.archived is True
    assert result.duplicate is False
    assert len(archive.list_news()) == 1
    assert len(archive.list_events()) == 1


def test_import_kaynak_adi_kanonik_kaydedilir(tmp_path):
    svc, archive = service(tmp_path)
    svc.import_item(item(source_name="reuters", source_reference=""))
    saved = archive.list_news()[0]
    assert saved.source_name == "Reuters"
    assert saved.source_tier is SourceTier.TIER_2_MAJOR_FINANCIAL


def test_import_olay_alanlarini_korur(tmp_path):
    svc, archive = service(tmp_path)
    svc.import_item(item(
        event_title="Şirket açıklaması",
        event_type=EventType.KAP_ACIKLAMASI,
        market_scope=MarketScope.COMPANY,
        symbols=("THYAO",),
        sectors=("Havacılık",),
    ))
    event = archive.list_events()[0]
    assert event.title == "Şirket açıklaması"
    assert event.event_type is EventType.KAP_ACIKLAMASI
    assert event.market_scope is MarketScope.COMPANY
    assert event.symbols == ("THYAO.IS",)
    assert event.sectors == ("Havacılık",)


def test_ayni_kayit_ikinci_kez_duplicate_olarak_doner(tmp_path):
    svc, archive = service(tmp_path)
    first = svc.import_item(item())
    second = svc.import_item(item())
    assert first.archived is True
    assert second.archived is False
    assert second.duplicate is True
    assert len(archive.list_news()) == 1


def test_preview_duplicate_mevcut_haber_kimligini_verir(tmp_path):
    svc, _ = service(tmp_path)
    first = svc.import_item(item())
    preview = svc.preview(item())
    assert preview.duplicate is True
    assert preview.existing_news_id == first.archive_result.news.news_id


def test_hash_kaynak_kanonik_ada_gore_ayni(tmp_path):
    svc, _ = service(tmp_path)
    a = svc.preview(item(source_name="Reuters", source_reference=""))
    b = svc.preview(item(source_name="reuters", source_reference=""))
    assert a.content_hash == b.content_hash


def test_farkli_kaynak_ayni_baslik_duplicate_sayilmaz(tmp_path):
    svc, _ = service(tmp_path)
    a = svc.preview(item(source_name="Reuters", source_reference=""))
    b = svc.preview(item(source_name="Bloomberg", source_reference=""))
    assert a.content_hash != b.content_hash


def test_farkli_yayin_zamani_duplicate_sayilmaz(tmp_path):
    svc, _ = service(tmp_path)
    later = NOW.replace(minute=1)
    a = svc.preview(item())
    b = svc.preview(item(published_at=later))
    assert a.content_hash != b.content_hash


def test_saat_dilimsiz_yayin_reddedilir():
    with pytest.raises(ValueError, match="saat dilimi"):
        item(published_at=datetime(2026, 8, 5, 18, 0))


def test_hisse_metinden_tahmin_edilmez(tmp_path):
    svc, archive = service(tmp_path)
    svc.import_item(item(headline="THYAO haberi", symbols=()))
    event = archive.list_events()[0]
    assert event.symbols == ()


def test_dis_adapter_event_id_verirse_mevcut_olaya_baglanabilir(tmp_path):
    svc, archive = service(tmp_path)
    first = svc.import_item(item(headline="İlk", body="İlk içerik"))
    event_id = first.archive_result.event.event_id
    second = svc.import_item(
        item(
            source_name="Bloomberg",
            source_reference="",
            headline="İkinci",
            body="İkinci içerik",
        ),
        existing_event_id=event_id,
    )
    assert second.archived is True
    assert len(archive.list_events()) == 1
    assert len(archive.list_news()) == 2


def test_preview_many_arsivi_yalniz_bir_kez_okur(tmp_path, monkeypatch):
    svc, archive = service(tmp_path)
    calls = 0
    original = archive.list_news

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(archive, "list_news", counted)
    previews = svc.preview_many([
        item(headline="Bir", body="Bir"),
        item(headline="İki", body="İki", published_at=NOW.replace(minute=1)),
        item(headline="Üç", body="Üç", published_at=NOW.replace(minute=2)),
    ])
    assert len(previews) == 3
    assert calls == 1


def test_preview_many_ayni_akistaki_tekrari_yeni_saymaz(tmp_path):
    svc, _ = service(tmp_path)
    repeated = item()
    previews = svc.preview_many([repeated, repeated])
    assert previews[0].duplicate is False
    assert previews[1].duplicate is True
    assert previews[1].existing_news_id == ""


def test_import_preview_yeniden_tum_arsivi_taramaz(tmp_path, monkeypatch):
    svc, archive = service(tmp_path)
    preview = svc.preview(item())

    def forbidden(*args, **kwargs):
        raise AssertionError("import_preview tekrar arşiv taraması yapmamalı")

    monkeypatch.setattr(archive, "list_news", forbidden)
    result = svc.import_preview(preview)
    assert result.archived is True
