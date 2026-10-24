from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.archive import NewsArchive
from backend.app.news_center.feed_ingestion import FeedIngestionService
from backend.app.news_center.models import EventType, MarketScope, SourceTier
from backend.app.news_center.tuik_adapter import (
    TuikAdapterError,
    TuikPressUrlAdapter,
    parse_tuik_press_html,
    validate_tuik_press_url,
)

IST = ZoneInfo("Europe/Istanbul")
URL = "https://veriportali.tuik.gov.tr/tr/press/58175"
HTML = """
<html><body>
<div>Yayım Tarihi:23 Temmuz 2026 10:00</div>
<div>Sayı:58175</div>
<h1>Tüketici Güven Endeksi, Temmuz 2026</h1>
<h2>Tüketici güven endeksi 89,8 oldu</h2>
<p>Türkiye İstatistik Kurumu ve Türkiye Cumhuriyet Merkez Bankası işbirliği ile yürütülen tüketici eğilim anketi sonuçlarından hesaplanan tüketici güven endeksi 89,8 oldu.</p>
<div>Bu konu ile ilgili bir sonraki haber bülteninin yayımlanma tarihi: 21 Ağustos 2026</div>
</body></html>
"""


def test_tuik_url_dogrulanir():
    value, bulletin_id = validate_tuik_press_url(URL)
    assert value == URL
    assert bulletin_id == "58175"


@pytest.mark.parametrize("url", (
    "http://veriportali.tuik.gov.tr/tr/press/58175",
    "https://evil.example/tr/press/58175",
    "https://www.tuik.gov.tr/tr/press/58175",
    "https://data.tuik.gov.tr/tr/press/58175",
    "https://veriportali.tuik.gov.tr/Bulten/Index",
    "https://veriportali.tuik.gov.tr/tr/press/58175?x=1",
    "https://user@veriportali.tuik.gov.tr/tr/press/58175",
))
def test_guvensiz_tuik_url_reddedilir(url):
    with pytest.raises(TuikAdapterError):
        validate_tuik_press_url(url)


def test_tuik_html_feed_item_uretir():
    result = parse_tuik_press_html(HTML, source_url=URL)
    item = result.item
    assert result.bulletin_id == "58175"
    assert item.source_name == "TÜİK"
    assert item.external_id == "58175"
    assert item.published_at == datetime(2026, 7, 23, 10, 0, tzinfo=IST)
    assert item.market_scope is MarketScope.TURKEY_MACRO
    assert item.event_type is EventType.DIGER
    assert item.symbols == ()
    assert item.sectors == ()


def test_baslik_ilk_anlamli_headingden_gelir():
    assert parse_tuik_press_html(HTML, source_url=URL).item.headline == "Tüketici Güven Endeksi, Temmuz 2026"


def test_govde_gorunur_metinden_gelir():
    assert "tüketici eğilim anketi" in parse_tuik_press_html(HTML, source_url=URL).item.body


def test_script_icerigi_govdeye_girmez():
    html = HTML.replace("</body>", "<script>THYAO gizli kod</script></body>")
    assert "THYAO gizli kod" not in parse_tuik_press_html(html, source_url=URL).item.body


def test_hisse_ve_sektor_tahmini_yok():
    html = HTML.replace("89,8 oldu.", "89,8 oldu. THYAO ASELS Bankacılık.", 1)
    item = parse_tuik_press_html(html, source_url=URL).item
    assert item.symbols == ()
    assert item.sectors == ()


@pytest.mark.parametrize("title,event_type", (
    ("Tüketici Fiyat Endeksi, Haziran 2026", EventType.ENFLASYON),
    ("Yurt İçi Üretici Fiyat Endeksi, Haziran 2026", EventType.ENFLASYON),
    ("İşgücü İstatistikleri, Haziran 2026", EventType.ISTIHDAM),
    ("Dönemsel Gayrisafi Yurt İçi Hasıla, I. Çeyrek 2026", EventType.BUYUME),
    ("Sanayi Üretim Endeksi, Mayıs 2026", EventType.SEKTOR),
))
def test_deterministik_olay_turu(title, event_type):
    html = HTML.replace("Tüketici Güven Endeksi, Temmuz 2026", title, 1)
    assert parse_tuik_press_html(html, source_url=URL).item.event_type is event_type


def test_url_ve_sayi_uyusmazsa_reddedilir():
    with pytest.raises(TuikAdapterError, match="uyuşmuyor"):
        parse_tuik_press_html(HTML.replace("Sayı:58175", "Sayı:99999"), source_url=URL)


def test_yayim_tarihi_yoksa_reddedilir():
    with pytest.raises(TuikAdapterError, match="Yayım Tarihi"):
        parse_tuik_press_html(HTML.replace("Yayım Tarihi:23 Temmuz 2026 10:00", ""), source_url=URL)


def test_sayi_yoksa_reddedilir():
    with pytest.raises(TuikAdapterError, match="Sayı"):
        parse_tuik_press_html(HTML.replace("Sayı:58175", ""), source_url=URL)


def test_ag_varsayilan_kapali():
    with pytest.raises(TuikAdapterError, match="ağ erişimi kapalı"):
        TuikPressUrlAdapter().fetch(URL)


def test_acik_ag_injected_fetcher():
    calls = []
    def fetcher(url, timeout):
        calls.append((url, timeout))
        return HTML.encode("utf-8"), URL, "text/html; charset=utf-8"
    result = TuikPressUrlAdapter(network_enabled=True, fetcher=fetcher).fetch(URL)
    assert calls == [(URL, 10)]
    assert result.bulletin_id == "58175"


def test_redirect_farkli_host_reddedilir():
    def fetcher(url, timeout):
        return HTML.encode(), "https://evil.example/tr/press/58175", "text/html"
    with pytest.raises(TuikAdapterError, match="veriportali.tuik.gov.tr"):
        TuikPressUrlAdapter(network_enabled=True, fetcher=fetcher).fetch(URL)


def test_redirect_farkli_bulten_reddedilir():
    def fetcher(url, timeout):
        return HTML.encode(), "https://veriportali.tuik.gov.tr/tr/press/58176", "text/html"
    with pytest.raises(TuikAdapterError, match="farklı bir bülten"):
        TuikPressUrlAdapter(network_enabled=True, fetcher=fetcher).fetch(URL)


def test_html_disinda_yanit_reddedilir():
    def fetcher(url, timeout):
        return b"{}", URL, "application/json"
    with pytest.raises(TuikAdapterError, match="HTML değil"):
        TuikPressUrlAdapter(network_enabled=True, fetcher=fetcher).fetch(URL)


@pytest.mark.parametrize("timeout", (0, 31))
def test_timeout_siniri(timeout):
    with pytest.raises(ValueError, match="timeout_seconds"):
        TuikPressUrlAdapter(timeout_seconds=timeout)


def test_feed_ingestion_dry_run_ile_uyumlu(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_tuik_press_html(HTML, source_url=URL).item
    preview = service.preview(item)
    assert preview.source.canonical_name == "TÜİK"
    assert preview.source.tier is SourceTier.TIER_1_OFFICIAL
    assert preview.duplicate is False
    assert archive.list_news() == ()


def test_acik_import_ile_tuik_arsivlenir(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_tuik_press_html(HTML, source_url=URL).item
    result = service.import_item(item)
    assert result.archived is True
    saved = archive.list_news()[0]
    assert saved.source_name == "TÜİK"
    assert saved.source_tier is SourceTier.TIER_1_OFFICIAL
    event = archive.list_events()[0]
    assert event.market_scope is MarketScope.TURKEY_MACRO
    assert event.symbols == ()
    assert event.sectors == ()


def test_ikinci_import_duplicate(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_tuik_press_html(HTML, source_url=URL).item
    assert service.import_item(item).archived is True
    second = service.import_item(item)
    assert second.archived is False
    assert second.duplicate is True
