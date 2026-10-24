from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.archive import NewsArchive
from backend.app.news_center.feed_ingestion import FeedIngestionService
from backend.app.news_center.hmb_adapter import (
    HmbAdapterError,
    HmbPressUrlAdapter,
    parse_hmb_press_html,
    validate_hmb_press_url,
)
from backend.app.news_center.models import EventType, MarketScope, SourceTier


IST = ZoneInfo("Europe/Istanbul")
URL = "https://www.hmb.gov.tr/duyuru/basin-duyurusu-12-04-2026"
URL_HABER = "https://www.hmb.gov.tr/haberler/finansal-istikrar-komitesi-toplantisina-iliskin-basin-duyurusu-22-05-2026"

HTML = """
<html><head><title>HMB</title></head><body>
<h1>Basın Duyurusu – 12.04.2026</h1>
<div>12 Nisan 2026</div>
<p>Bakanlığımız borçlanma politikası orta ve uzun vadeli stratejik ölçütler
çerçevesinde yürütülmektedir.</p>
<p>Kamuoyuna saygıyla duyurulur.</p>
<div>Dikmen Yerleşkesi Adres: T.C. Hazine ve Maliye Bakanlığı</div>
<div>Telefon: 0 (312) 415-29 00</div>
</body></html>
"""


def test_hmb_duyuru_url_dogrulanir():
    value, announcement_id = validate_hmb_press_url(URL)
    assert value == URL
    assert announcement_id == "duyuru:basin-duyurusu-12-04-2026"


def test_hmb_haberler_url_dogrulanir():
    value, announcement_id = validate_hmb_press_url(URL_HABER)
    assert value == URL_HABER
    assert announcement_id.startswith("haberler:")


@pytest.mark.parametrize(
    "url",
    (
        "http://www.hmb.gov.tr/duyuru/test",
        "https://evil.example/duyuru/test",
        "https://www.hmb.gov.tr/",
        "https://www.hmb.gov.tr/duyurular/test",
        "https://www.hmb.gov.tr/kamu-finansmani-genel-mudurlugu-duyurular",
        "https://www.hmb.gov.tr/duyuru/test?x=1",
        "https://user@www.hmb.gov.tr/duyuru/test",
    ),
)
def test_guvensiz_hmb_url_reddedilir(url):
    with pytest.raises(HmbAdapterError):
        validate_hmb_press_url(url)


def test_hmb_html_feed_item_uretir():
    result = parse_hmb_press_html(HTML, source_url=URL)
    item = result.item
    assert item.source_name == "Hazine ve Maliye Bakanlığı"
    assert item.published_at == datetime(2026, 4, 12, 12, 0, tzinfo=IST)
    assert item.headline == "Basın Duyurusu – 12.04.2026"
    assert item.event_type is EventType.DIGER
    assert item.market_scope is MarketScope.OTHER
    assert item.symbols == ()
    assert item.sectors == ()


def test_genel_baslik_govdeden_borclanma_tahmini_yapmaz():
    result = parse_hmb_press_html(HTML, source_url=URL)
    assert "borçlanma" in result.item.body
    assert result.item.event_type is EventType.DIGER
    assert result.item.market_scope is MarketScope.OTHER


def test_footer_govdeye_girmez():
    result = parse_hmb_press_html(HTML, source_url=URL)
    assert "Kamuoyuna saygıyla" in result.item.body
    assert "Dikmen Yerleşkesi" not in result.item.body
    assert "415-29-00" not in result.item.body


def test_script_icerigi_govdeye_girmez():
    html = HTML.replace("</body>", "<script>THYAO ASELS gizli</script></body>")
    result = parse_hmb_press_html(html, source_url=URL)
    assert "gizli" not in result.item.body


def test_hisse_ve_sektor_tahmini_yok():
    html = HTML.replace("Kamuoyuna saygıyla duyurulur.", "THYAO ASELS Bankacılık.")
    result = parse_hmb_press_html(html, source_url=URL)
    assert result.item.symbols == ()
    assert result.item.sectors == ()


@pytest.mark.parametrize(
    "title",
    (
        "Haziran – Ağustos 2026 İç Borçlanma Stratejisi",
        "8 Haziran 2026 Tarihinde Gerçekleştirilen İhalenin Sonuçlarına İlişkin Basın Duyurusu",
        "ABD Doları Cinsi Devlet Tahvili İhracına İlişkin Basın Duyurusu",
        "Kira Sertifikası İhracına İlişkin Basın Duyurusu",
        "Mayıs 2026 Hazine Nakit Gerçekleşmeleri",
    ),
)
def test_borclanma_basliklari_finansman(title):
    html = HTML.replace("Basın Duyurusu – 12.04.2026", title, 1)
    item = parse_hmb_press_html(html, source_url=URL).item
    assert item.event_type is EventType.BORCLANMA_FINANSMAN
    assert item.market_scope is MarketScope.TURKEY_MACRO


def test_enflasyon_basligi_enflasyon():
    html = HTML.replace(
        "Basın Duyurusu – 12.04.2026",
        "Enflasyon ve Fiyat İstikrarına İlişkin Basın Duyurusu",
        1,
    )
    item = parse_hmb_press_html(html, source_url=URL).item
    assert item.event_type is EventType.ENFLASYON
    assert item.market_scope is MarketScope.TURKEY_MACRO


def test_doviz_basligi_doviz():
    html = HTML.replace(
        "Basın Duyurusu – 12.04.2026",
        "Döviz Piyasalarına İlişkin Basın Duyurusu",
        1,
    )
    item = parse_hmb_press_html(html, source_url=URL).item
    assert item.event_type is EventType.DOVIZ
    assert item.market_scope is MarketScope.TURKEY_MACRO


def test_finansal_istikrar_basligi_macro_diger():
    html = HTML.replace(
        "Basın Duyurusu – 12.04.2026",
        "Finansal İstikrar Komitesi Toplantısına İlişkin Basın Duyurusu",
        1,
    )
    item = parse_hmb_press_html(html, source_url=URL).item
    assert item.event_type is EventType.DIGER
    assert item.market_scope is MarketScope.TURKEY_MACRO


def test_tarih_yoksa_reddedilir():
    html = HTML.replace("12 Nisan 2026", "")
    with pytest.raises(HmbAdapterError, match="tarihi"):
        parse_hmb_press_html(html, source_url=URL)


def test_ag_varsayilan_kapali():
    with pytest.raises(HmbAdapterError, match="ağ erişimi kapalı"):
        HmbPressUrlAdapter().fetch(URL)


def test_acik_ag_injected_fetcher():
    calls = []
    def fetcher(url, timeout):
        calls.append((url, timeout))
        return HTML.encode("utf-8"), URL, "text/html; charset=utf-8"
    result = HmbPressUrlAdapter(network_enabled=True, fetcher=fetcher).fetch(URL)
    assert calls == [(URL, 10)]
    assert result.item.source_name == "Hazine ve Maliye Bakanlığı"


def test_redirect_farkli_host_reddedilir():
    def fetcher(url, timeout):
        return HTML.encode(), "https://evil.example/duyuru/test", "text/html"
    with pytest.raises(HmbAdapterError, match="hmb.gov.tr"):
        HmbPressUrlAdapter(network_enabled=True, fetcher=fetcher).fetch(URL)


def test_redirect_farkli_duyuru_reddedilir():
    def fetcher(url, timeout):
        return HTML.encode(), "https://www.hmb.gov.tr/duyuru/baska-duyuru", "text/html"
    with pytest.raises(HmbAdapterError, match="farklı bir duyuru"):
        HmbPressUrlAdapter(network_enabled=True, fetcher=fetcher).fetch(URL)


def test_html_disinda_yanit_reddedilir():
    def fetcher(url, timeout):
        return b"{}", URL, "application/json"
    with pytest.raises(HmbAdapterError, match="HTML değil"):
        HmbPressUrlAdapter(network_enabled=True, fetcher=fetcher).fetch(URL)


@pytest.mark.parametrize("timeout", (0, 31))
def test_timeout_siniri(timeout):
    with pytest.raises(ValueError, match="timeout_seconds"):
        HmbPressUrlAdapter(timeout_seconds=timeout)


def test_feed_ingestion_dry_run_ile_uyumlu(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_hmb_press_html(HTML, source_url=URL).item
    preview = service.preview(item)
    assert preview.source.canonical_name == "Hazine ve Maliye Bakanlığı"
    assert preview.source.tier is SourceTier.TIER_1_OFFICIAL
    assert preview.duplicate is False
    assert archive.list_news() == ()


def test_acik_import_ile_hmb_arsivlenir(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_hmb_press_html(HTML, source_url=URL).item
    result = service.import_item(item)
    assert result.archived is True
    saved = archive.list_news()[0]
    assert saved.source_name == "Hazine ve Maliye Bakanlığı"
    assert saved.source_tier is SourceTier.TIER_1_OFFICIAL


def test_ikinci_import_duplicate(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_hmb_press_html(HTML, source_url=URL).item
    assert service.import_item(item).archived is True
    second = service.import_item(item)
    assert second.archived is False
    assert second.duplicate is True
