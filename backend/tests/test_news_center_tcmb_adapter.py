from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.archive import NewsArchive
from backend.app.news_center.feed_ingestion import FeedIngestionService
from backend.app.news_center.models import EventType, MarketScope, SourceTier
from backend.app.news_center.tcmb_adapter import (
    TcmbAdapterError,
    TcmbPressUrlAdapter,
    parse_tcmb_press_html,
    validate_tcmb_press_url,
)


IST = ZoneInfo("Europe/Istanbul")
URL = (
    "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB%2BTR/"
    "Main%2BMenu/Duyurular/Basin/2026/DUY2026-28"
)

HTML = """
<html>
<head><title>TCMB</title></head>
<body>
<h1>Faiz Oranlarına İlişkin Basın Duyurusu (2026-28)</h1>
<div>Sayı: 2026-28</div>
<div>23 Temmuz 2026</div>
<h2>Faiz Oranlarına İlişkin Basın Duyurusu</h2>
<p>Para Politikası Kurulu, politika faizini yüzde 37 düzeyinde sabit tutmuştur.</p>
<p>Enflasyon görünümü yakından takip edilmektedir.</p>
</body>
</html>
"""


def test_tcmb_url_dogrulanir():
    value, bulletin_id = validate_tcmb_press_url(URL)
    assert value == URL
    assert bulletin_id == "2026-28"


@pytest.mark.parametrize(
    "url",
    (
        "http://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Basin/2026/DUY2026-28",
        "https://evil.example/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Basin/2026/DUY2026-28",
        "https://www.tcmb.gov.tr/",
        "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Basin",
        "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Basin/2026/DUY2025-28",
        "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Basin/2026/DUY2026-28?x=1",
        "https://user@www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Basin/2026/DUY2026-28",
    ),
)
def test_guvensiz_tcmb_url_reddedilir(url):
    with pytest.raises(TcmbAdapterError):
        validate_tcmb_press_url(url)


def test_tcmb_html_feed_item_uretir():
    result = parse_tcmb_press_html(HTML, source_url=URL)
    item = result.item

    assert result.bulletin_id == "2026-28"
    assert item.source_name == "TCMB"
    assert item.external_id == "2026-28"
    assert item.published_at == datetime(2026, 7, 23, 12, 0, tzinfo=IST)
    assert item.market_scope is MarketScope.TURKEY_MACRO
    assert item.event_type is EventType.PARA_POLITIKASI
    assert item.symbols == ()
    assert item.sectors == ()


def test_baslik_headingden_gelir():
    result = parse_tcmb_press_html(HTML, source_url=URL)
    assert "Faiz Oranlarına İlişkin" in result.item.headline


def test_govde_gorunur_metinden_gelir():
    result = parse_tcmb_press_html(HTML, source_url=URL)
    assert "politika faizini" in result.item.body


def test_script_icerigi_govdeye_girmez():
    html = HTML.replace(
        "</body>",
        "<script>THYAO gizli kod</script></body>",
    )
    result = parse_tcmb_press_html(html, source_url=URL)
    assert "THYAO gizli kod" not in result.item.body


def test_hisse_tahmini_yok():
    html = HTML.replace(
        "Enflasyon görünümü yakından takip edilmektedir.",
        "THYAO ve ASELS isimleri metinde geçebilir.",
    )
    result = parse_tcmb_press_html(html, source_url=URL)
    assert result.item.symbols == ()


def test_makroihtiyati_baslik_regulasyon():
    html = HTML.replace(
        "Faiz Oranlarına İlişkin Basın Duyurusu (2026-28)",
        "Makroihtiyati Çerçeveye İlişkin Basın Duyurusu (2026-28)",
        1,
    )
    result = parse_tcmb_press_html(html, source_url=URL)
    assert result.item.event_type is EventType.REGULASYON


def test_doviz_baslik_doviz():
    html = HTML.replace(
        "Faiz Oranlarına İlişkin Basın Duyurusu (2026-28)",
        "Döviz Piyasalarına İlişkin Basın Duyurusu (2026-28)",
        1,
    )
    result = parse_tcmb_press_html(html, source_url=URL)
    assert result.item.event_type is EventType.DOVIZ


def test_bagimsiz_kur_ifadesi_doviz():
    html = HTML.replace(
        "Faiz Oranlarına İlişkin Basın Duyurusu (2026-28)",
        "Kur Gelişmelerine İlişkin Basın Duyurusu (2026-28)",
        1,
    )
    result = parse_tcmb_press_html(html, source_url=URL)
    assert result.item.event_type is EventType.DOVIZ


def test_kurumsal_kelimesi_doviz_sayilmaz():
    html = HTML.replace(
        "Faiz Oranlarına İlişkin Basın Duyurusu (2026-28)",
        "Kurumsal Bilgilendirme Basın Duyurusu (2026-28)",
        1,
    )
    result = parse_tcmb_press_html(html, source_url=URL)
    assert result.item.event_type is EventType.DIGER


def test_tarih_yoksa_reddedilir():
    html = HTML.replace("23 Temmuz 2026", "")
    with pytest.raises(TcmbAdapterError, match="tarihi"):
        parse_tcmb_press_html(html, source_url=URL)


def test_ag_varsayilan_kapali():
    adapter = TcmbPressUrlAdapter()
    with pytest.raises(TcmbAdapterError, match="ağ erişimi kapalı"):
        adapter.fetch(URL)


def test_acik_ag_injected_fetcher():
    calls = []

    def fetcher(url, timeout):
        calls.append((url, timeout))
        return HTML.encode("utf-8"), URL, "text/html; charset=utf-8"

    result = TcmbPressUrlAdapter(
        network_enabled=True,
        fetcher=fetcher,
    ).fetch(URL)

    assert calls == [(URL, 10)]
    assert result.bulletin_id == "2026-28"


def test_redirect_farkli_host_reddedilir():
    def fetcher(url, timeout):
        return (
            HTML.encode(),
            "https://evil.example/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Basin/2026/DUY2026-28",
            "text/html",
        )

    with pytest.raises(TcmbAdapterError, match="tcmb.gov.tr"):
        TcmbPressUrlAdapter(
            network_enabled=True,
            fetcher=fetcher,
        ).fetch(URL)


def test_redirect_farkli_duyuru_reddedilir():
    def fetcher(url, timeout):
        return (
            HTML.encode(),
            "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Basin/2026/DUY2026-29",
            "text/html",
        )

    with pytest.raises(TcmbAdapterError, match="farklı bir duyuru"):
        TcmbPressUrlAdapter(
            network_enabled=True,
            fetcher=fetcher,
        ).fetch(URL)


def test_html_disinda_yanit_reddedilir():
    def fetcher(url, timeout):
        return b"{}", URL, "application/json"

    with pytest.raises(TcmbAdapterError, match="HTML değil"):
        TcmbPressUrlAdapter(
            network_enabled=True,
            fetcher=fetcher,
        ).fetch(URL)


@pytest.mark.parametrize("timeout", (0, 31))
def test_timeout_siniri(timeout):
    with pytest.raises(ValueError, match="timeout_seconds"):
        TcmbPressUrlAdapter(timeout_seconds=timeout)


def test_feed_ingestion_dry_run_ile_uyumlu(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_tcmb_press_html(HTML, source_url=URL).item

    preview = service.preview(item)

    assert preview.source.canonical_name == "TCMB"
    assert preview.source.tier is SourceTier.TIER_1_OFFICIAL
    assert preview.duplicate is False
    assert archive.list_news() == ()


def test_acik_import_ile_tcmb_arsivlenir(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_tcmb_press_html(HTML, source_url=URL).item

    result = service.import_item(item)

    assert result.archived is True
    saved = archive.list_news()[0]
    assert saved.source_name == "TCMB"
    assert saved.source_tier is SourceTier.TIER_1_OFFICIAL
    event = archive.list_events()[0]
    assert event.market_scope is MarketScope.TURKEY_MACRO
    assert event.event_type is EventType.PARA_POLITIKASI


def test_ikinci_import_duplicate(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_tcmb_press_html(HTML, source_url=URL).item

    assert service.import_item(item).archived is True
    second = service.import_item(item)

    assert second.archived is False
    assert second.duplicate is True
