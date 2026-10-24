from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.archive import NewsArchive
from backend.app.news_center.feed_ingestion import (
    FeedIngestionService,
    feed_source_statuses,
)
from backend.app.news_center.kap_adapter import (
    KapAdapterError,
    KapUrlAdapter,
    parse_kap_detail_html,
    validate_kap_detail_url,
)
from backend.app.news_center.models import EventType, MarketScope, SourceTier


IST = ZoneInfo("Europe/Istanbul")
URL = "https://www.kap.org.tr/tr/Bildirim/1636759"

HTML = """
<html><body>
<h1>Kamuyu Aydınlatma Platformu Duyurusu</h1>
<div>Gönderim Tarihi</div><div>27.07.2026 08:50:15</div>
<div>Bildirim Tipi</div><div>DKB</div>
<div>Özet Bilgi</div>
<div>Özel Durumlar Tebliği'nin 12-(4). maddesi gereğince yapılan açıklama</div>
<div>İlgili Şirketler</div><div>DITAS, FZLGY, MANAS, TKFEN</div>
<div>İlgili Fonlar</div><div>YLZ, PYH</div>
<div>Açıklamalar</div>
<div>Sermaye Piyasası Kurulu düzenlemesi kapsamında yapılan açıklama.</div>
<div>Bildirimlerin MKK tarafından aktarıldığına ilişkin dipnot</div>
</body></html>
"""


def test_kap_detay_url_dogrulanir():
    value, notification_id = validate_kap_detail_url(URL)
    assert value == URL
    assert notification_id == "1636759"


@pytest.mark.parametrize(
    "url",
    (
        "http://www.kap.org.tr/tr/Bildirim/1",
        "https://evil.example/tr/Bildirim/1",
        "https://www.kap.org.tr/tr/bildirim-sorgu-sonuc",
        "https://www.kap.org.tr/tr/Bildirim/1?x=1",
        "https://user@www.kap.org.tr/tr/Bildirim/1",
    ),
)
def test_guvensiz_url_reddedilir(url):
    with pytest.raises(KapAdapterError):
        validate_kap_detail_url(url)


def test_html_kap_feed_item_uretir():
    result = parse_kap_detail_html(HTML, source_url=URL)
    item = result.item
    assert result.notification_id == "1636759"
    assert item.source_name == "KAP"
    assert item.external_id == "1636759"
    assert item.published_at == datetime(2026, 7, 27, 8, 50, 15, tzinfo=IST)
    assert item.event_type is EventType.KAP_ACIKLAMASI
    assert item.market_scope is MarketScope.COMPANY
    assert item.symbols == (
        "DITAS.IS",
        "FZLGY.IS",
        "MANAS.IS",
        "TKFEN.IS",
    )


def test_hisse_yalniz_ilgili_sirketler_alanindan():
    html = HTML.replace(
        "<div>İlgili Şirketler</div><div>DITAS, FZLGY, MANAS, TKFEN</div>",
        "<div>İlgili Şirketler</div><div>TKFEN</div>",
    ).replace(
        "Sermaye Piyasası Kurulu düzenlemesi kapsamında yapılan açıklama.",
        "THYAO ve ASELS metinde geçiyor ama ilgili şirket değildir.",
    )
    result = parse_kap_detail_html(html, source_url=URL)
    assert result.item.symbols == ("TKFEN.IS",)


def test_sektor_tahmini_yok():
    result = parse_kap_detail_html(HTML, source_url=URL)
    assert result.item.sectors == ()


def test_ozet_yoksa_guvenli_baslik_fallback():
    html = HTML.replace(
        "<div>Özet Bilgi</div>\n<div>Özel Durumlar Tebliği'nin 12-(4). maddesi gereğince yapılan açıklama</div>",
        "",
    )
    result = parse_kap_detail_html(html, source_url=URL)
    assert result.item.headline == "KAP Bildirimi 1636759"


def test_aciklama_yoksa_body_ozetten_gelir():
    html = HTML.replace(
        "<div>Açıklamalar</div>\n<div>Sermaye Piyasası Kurulu düzenlemesi kapsamında yapılan açıklama.</div>",
        "",
    )
    result = parse_kap_detail_html(html, source_url=URL)
    assert "Özel Durumlar Tebliği" in result.item.body


def test_gonderim_tarihi_yoksa_reddedilir():
    html = HTML.replace(
        "<div>Gönderim Tarihi</div><div>27.07.2026 08:50:15</div>",
        "",
    )
    with pytest.raises(KapAdapterError, match="Gönderim Tarihi"):
        parse_kap_detail_html(html, source_url=URL)


def test_ag_varsayilan_kapali():
    adapter = KapUrlAdapter()
    with pytest.raises(KapAdapterError, match="ağ erişimi kapalı"):
        adapter.fetch(URL)


def test_acik_ag_sadece_injected_fetcher_ile_calisir():
    calls = []

    def fetcher(url, timeout):
        calls.append((url, timeout))
        return HTML.encode("utf-8"), URL, "text/html; charset=utf-8"

    adapter = KapUrlAdapter(network_enabled=True, fetcher=fetcher)
    result = adapter.fetch(URL)
    assert calls == [(URL, 10)]
    assert result.notification_id == "1636759"


def test_redirect_farkli_host_reddedilir():
    def fetcher(url, timeout):
        return HTML.encode(), "https://evil.example/tr/Bildirim/1636759", "text/html"

    adapter = KapUrlAdapter(network_enabled=True, fetcher=fetcher)
    with pytest.raises(KapAdapterError, match="kap.org.tr"):
        adapter.fetch(URL)


def test_redirect_farkli_bildirim_reddedilir():
    def fetcher(url, timeout):
        return HTML.encode(), "https://www.kap.org.tr/tr/Bildirim/99", "text/html"

    adapter = KapUrlAdapter(network_enabled=True, fetcher=fetcher)
    with pytest.raises(KapAdapterError, match="farklı bir bildirim"):
        adapter.fetch(URL)


def test_html_disinda_yanit_reddedilir():
    def fetcher(url, timeout):
        return b"{}", URL, "application/json"

    adapter = KapUrlAdapter(network_enabled=True, fetcher=fetcher)
    with pytest.raises(KapAdapterError, match="HTML değil"):
        adapter.fetch(URL)


@pytest.mark.parametrize("timeout", (0, 31))
def test_timeout_siniri(timeout):
    with pytest.raises(ValueError, match="timeout_seconds"):
        KapUrlAdapter(timeout_seconds=timeout)


def test_kap_adapter_feed_ingestion_dry_run_ile_uyumlu(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_kap_detail_html(HTML, source_url=URL).item
    preview = service.preview(item)

    assert preview.source.canonical_name == "KAP"
    assert preview.source.tier is SourceTier.TIER_1_OFFICIAL
    assert preview.duplicate is False
    assert archive.list_news() == ()


def test_acik_import_ile_kap_arsivlenir(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_kap_detail_html(HTML, source_url=URL).item

    result = service.import_item(item)

    assert result.archived is True
    saved = archive.list_news()[0]
    assert saved.source_name == "KAP"
    assert saved.source_tier is SourceTier.TIER_1_OFFICIAL
    event = archive.list_events()[0]
    assert event.event_type is EventType.KAP_ACIKLAMASI
    assert event.symbols == item.symbols


def test_ikinci_import_duplicate(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_kap_detail_html(HTML, source_url=URL).item

    first = service.import_item(item)
    second = service.import_item(item)

    assert first.archived is True
    assert second.archived is False
    assert second.duplicate is True


def test_status_api_default_eski_davranisi_korur():
    assert all(row.adapter_enabled is False for row in feed_source_statuses())


def test_status_api_kap_adapterini_acik_gosterebilir():
    statuses = feed_source_statuses(("KAP",))
    kap = next(row for row in statuses if row.canonical_name == "KAP")
    tcmb = next(row for row in statuses if row.canonical_name == "TCMB")
    assert kap.adapter_enabled is True
    assert tcmb.adapter_enabled is False
