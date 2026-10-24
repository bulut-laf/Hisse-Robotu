from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.archive import NewsArchive
from backend.app.news_center.feed_ingestion import FeedIngestionService
from backend.app.news_center.models import EventType, MarketScope, SourceTier
from backend.app.news_center.spk_adapter import (
    SpkAdapterError,
    SpkPressUrlAdapter,
    parse_spk_press_html,
    validate_spk_press_url,
)


IST = ZoneInfo("Europe/Istanbul")
URL = (
    "https://spk.gov.tr/duyurular/basin-duyurulari/2026/"
    "dolandiricilik-girisimlerine-iliskin-duyuru"
)

HTML = """
<html>
<head><title>SPK</title></head>
<body>
<h1>Dolandırıcılık Girişimlerine İlişkin Duyuru</h1>
<div>12 Haziran 2026</div>
<p>Son dönemde kendilerini Sermaye Piyasası Kurulu yöneticileri olarak
tanıtan kişiler hakkında bildirimler alınmaktadır.</p>
<p>Kurulumuz ve personelinin para veya bağış talebinde bulunması söz konusu değildir.</p>
<div>Duyuruyu PDF formatında indirmek için tıklayınız.</div>
<div>Merkez Telefon +90 (312) 292 90 90</div>
</body>
</html>
"""


def test_spk_url_dogrulanir():
    value, announcement_id = validate_spk_press_url(URL)
    assert value == URL
    assert announcement_id == "2026:dolandiricilik-girisimlerine-iliskin-duyuru"


@pytest.mark.parametrize(
    "url",
    (
        "http://spk.gov.tr/duyurular/basin-duyurulari/2026/test",
        "https://evil.example/duyurular/basin-duyurulari/2026/test",
        "https://spk.gov.tr/duyurular",
        "https://spk.gov.tr/duyurular/basin-duyurulari/2026",
        "https://spk.gov.tr/duyurular/baskanin-konusmalari/2026/test",
        "https://spk.gov.tr/duyurular/basin-duyurulari/2026/test?x=1",
        "https://user@spk.gov.tr/duyurular/basin-duyurulari/2026/test",
    ),
)
def test_guvensiz_spk_url_reddedilir(url):
    with pytest.raises(SpkAdapterError):
        validate_spk_press_url(url)


def test_spk_html_feed_item_uretir():
    result = parse_spk_press_html(HTML, source_url=URL)
    item = result.item

    assert result.announcement_id == (
        "2026:dolandiricilik-girisimlerine-iliskin-duyuru"
    )
    assert item.source_name == "SPK"
    assert item.published_at == datetime(2026, 6, 12, 12, 0, tzinfo=IST)
    assert item.headline == "Dolandırıcılık Girişimlerine İlişkin Duyuru"
    assert item.event_type is EventType.DIGER
    assert item.market_scope is MarketScope.OTHER
    assert item.symbols == ()
    assert item.sectors == ()


def test_pdf_ve_iletisim_metni_govdeye_girmez():
    result = parse_spk_press_html(HTML, source_url=URL)
    assert "para veya bağış" in result.item.body
    assert "PDF formatında" not in result.item.body
    assert "Merkez Telefon" not in result.item.body


def test_script_icerigi_govdeye_girmez():
    html = HTML.replace(
        "</body>",
        "<script>THYAO ASELS gizli içerik</script></body>",
    )
    result = parse_spk_press_html(html, source_url=URL)
    assert "gizli içerik" not in result.item.body


def test_hisse_ve_sektor_tahmini_yok():
    html = HTML.replace(
        "para veya bağış talebinde bulunması söz konusu değildir.",
        "para veya bağış talebi yoktur. THYAO ASELS Bankacılık.",
    )
    result = parse_spk_press_html(html, source_url=URL)
    assert result.item.symbols == ()
    assert result.item.sectors == ()


@pytest.mark.parametrize(
    "title",
    (
        "Açığa Satış İşlemlerine İlişkin Tedbir Duyurusu",
        "Sermaye Piyasası Düzenlemelerine İlişkin Duyuru",
        "Pay Piyasası İşlemlerine İlişkin Kurul Kararı",
        "Piyasa Bozucu Eylemlere İlişkin Düzenleme",
        "İşlem Yasağı Tedbirine İlişkin Duyuru",
    ),
)
def test_acik_duzenleyici_baslik_regulasyon_ve_bist_wide(title):
    html = HTML.replace(
        "Dolandırıcılık Girişimlerine İlişkin Duyuru",
        title,
        1,
    )
    result = parse_spk_press_html(html, source_url=URL)
    assert result.item.event_type is EventType.REGULASYON
    assert result.item.market_scope is MarketScope.BIST_WIDE


def test_genel_egitim_duyurusu_piyasa_kapsami_uydurmaz():
    html = HTML.replace(
        "Dolandırıcılık Girişimlerine İlişkin Duyuru",
        "Üniversite Öğrencilerine Yönelik Eğitim Semineri Tamamlandı",
        1,
    )
    result = parse_spk_press_html(html, source_url=URL)
    assert result.item.event_type is EventType.DIGER
    assert result.item.market_scope is MarketScope.OTHER


def test_tarih_yoksa_reddedilir():
    html = HTML.replace("12 Haziran 2026", "")
    with pytest.raises(SpkAdapterError, match="tarihi"):
        parse_spk_press_html(html, source_url=URL)


def test_ag_varsayilan_kapali():
    adapter = SpkPressUrlAdapter()
    with pytest.raises(SpkAdapterError, match="ağ erişimi kapalı"):
        adapter.fetch(URL)


def test_acik_ag_injected_fetcher():
    calls = []

    def fetcher(url, timeout):
        calls.append((url, timeout))
        return HTML.encode("utf-8"), URL, "text/html; charset=utf-8"

    result = SpkPressUrlAdapter(
        network_enabled=True,
        fetcher=fetcher,
    ).fetch(URL)

    assert calls == [(URL, 10)]
    assert result.item.source_name == "SPK"


def test_redirect_farkli_host_reddedilir():
    def fetcher(url, timeout):
        return (
            HTML.encode(),
            "https://evil.example/duyurular/basin-duyurulari/2026/test",
            "text/html",
        )

    with pytest.raises(SpkAdapterError, match="spk.gov.tr"):
        SpkPressUrlAdapter(
            network_enabled=True,
            fetcher=fetcher,
        ).fetch(URL)


def test_redirect_farkli_duyuru_reddedilir():
    def fetcher(url, timeout):
        return (
            HTML.encode(),
            "https://spk.gov.tr/duyurular/basin-duyurulari/2026/baska-duyuru",
            "text/html",
        )

    with pytest.raises(SpkAdapterError, match="farklı bir duyuru"):
        SpkPressUrlAdapter(
            network_enabled=True,
            fetcher=fetcher,
        ).fetch(URL)


def test_html_disinda_yanit_reddedilir():
    def fetcher(url, timeout):
        return b"{}", URL, "application/json"

    with pytest.raises(SpkAdapterError, match="HTML değil"):
        SpkPressUrlAdapter(
            network_enabled=True,
            fetcher=fetcher,
        ).fetch(URL)


@pytest.mark.parametrize("timeout", (0, 31))
def test_timeout_siniri(timeout):
    with pytest.raises(ValueError, match="timeout_seconds"):
        SpkPressUrlAdapter(timeout_seconds=timeout)


def test_feed_ingestion_dry_run_ile_uyumlu(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_spk_press_html(HTML, source_url=URL).item

    preview = service.preview(item)

    assert preview.source.canonical_name == "SPK"
    assert preview.source.tier is SourceTier.TIER_1_OFFICIAL
    assert preview.duplicate is False
    assert archive.list_news() == ()


def test_acik_import_ile_spk_arsivlenir(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_spk_press_html(HTML, source_url=URL).item

    result = service.import_item(item)

    assert result.archived is True
    saved = archive.list_news()[0]
    assert saved.source_name == "SPK"
    assert saved.source_tier is SourceTier.TIER_1_OFFICIAL
    event = archive.list_events()[0]
    assert event.event_type is EventType.DIGER
    assert event.market_scope is MarketScope.OTHER


def test_ikinci_import_duplicate(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_spk_press_html(HTML, source_url=URL).item

    assert service.import_item(item).archived is True
    second = service.import_item(item)

    assert second.archived is False
    assert second.duplicate is True
