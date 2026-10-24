from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.archive import NewsArchive
from backend.app.news_center.borsa_istanbul_adapter import (
    BorsaIstanbulAdapterError,
    BorsaIstanbulAnnouncementUrlAdapter,
    parse_borsa_istanbul_announcement_html,
    validate_borsa_istanbul_announcement_url,
)
from backend.app.news_center.feed_ingestion import FeedIngestionService
from backend.app.news_center.models import EventType, MarketScope, SourceTier


IST = ZoneInfo("Europe/Istanbul")
URL = (
    "https://www.borsaistanbul.com/duyuru/15547/"
    "bist-geri-alim-endeksi-donemsel-degisiklikleri"
)

HTML = """
<html>
<head><title>Borsa İstanbul</title></head>
<body>
<h1>BIST Geri Alım Endeksi Dönemsel Değişiklikleri</h1>
<div>05.08.2026</div>
<p>BIST Geri Alım Endeksi kapsamında yer alacak payların belirlenmesine ilişkin
dönemsel değerleme çalışması tamamlanmıştır.</p>
<table>
<tr><td>AKSGY</td><td>ATAKP</td></tr>
</table>
<div>Borsa İstanbul A.Ş. © 2013-2025</div>
</body>
</html>
"""


def test_borsa_istanbul_url_dogrulanir():
    value, announcement_id = validate_borsa_istanbul_announcement_url(URL)
    assert value == URL
    assert announcement_id == (
        "15547:bist-geri-alim-endeksi-donemsel-degisiklikleri"
    )


@pytest.mark.parametrize(
    "url",
    (
        "http://www.borsaistanbul.com/duyuru/15547/test",
        "https://evil.example/duyuru/15547/test",
        "https://www.borsaistanbul.com/duyurular",
        "https://www.borsaistanbul.com/duyuru/15547",
        "https://www.borsaistanbul.com/endeksler/endeks-duyurulari",
        "https://www.borsaistanbul.com/duyuru/15547/test?x=1",
        "https://user@www.borsaistanbul.com/duyuru/15547/test",
        "https://www.borsaistanbul.com:8443/duyuru/15547/test",
    ),
)
def test_guvensiz_borsa_istanbul_url_reddedilir(url):
    with pytest.raises(BorsaIstanbulAdapterError):
        validate_borsa_istanbul_announcement_url(url)


def test_borsa_html_feed_item_uretir():
    result = parse_borsa_istanbul_announcement_html(HTML, source_url=URL)
    item = result.item

    assert result.announcement_id.startswith("15547:")
    assert item.source_name == "Borsa İstanbul"
    assert item.published_at == datetime(2026, 8, 5, 12, 0, tzinfo=IST)
    assert item.headline == "BIST Geri Alım Endeksi Dönemsel Değişiklikleri"
    assert item.event_type is EventType.DIGER
    assert item.market_scope is MarketScope.BIST_WIDE
    assert item.symbols == ()
    assert item.sectors == ()


def test_govde_gorunur_metinden_gelir():
    result = parse_borsa_istanbul_announcement_html(HTML, source_url=URL)
    assert "dönemsel değerleme" in result.item.body
    assert "Borsa İstanbul A.Ş. ©" not in result.item.body


def test_script_icerigi_govdeye_girmez():
    html = HTML.replace(
        "</body>",
        "<script>THYAO gizli kod</script></body>",
    )
    result = parse_borsa_istanbul_announcement_html(html, source_url=URL)
    assert "gizli kod" not in result.item.body


def test_hisse_kodlari_metinde_olsa_da_sembol_uretmez():
    result = parse_borsa_istanbul_announcement_html(HTML, source_url=URL)
    assert "AKSGY" in result.item.body
    assert result.item.symbols == ()


@pytest.mark.parametrize(
    "title",
    (
        "Pay Piyasası Prosedürü Değişiklikleri Hakkında Duyuru",
        "BIST Pay Endeksleri Kural Setinde Yapılan Değişiklikler Hakkında Duyuru",
        "Vadeli İşlem ve Opsiyon Piyasası Piyasa Yapıcılık Kurallarında Değişiklikler",
        "Yıldız Pazar, Ana Pazar ve Alt Pazarda İşlem Gören Payların Yeniden Belirlenmesi",
        "Pay Piyasasında Takas Süresinin Kısaltılması Hakkında Duyuru",
        "Pay Piyasasında Emir/İşlem Oranının Değiştirilmesi Hk. Duyuru",
        "Devre Kesici Uygulamasına İlişkin Değişiklik Hakkında Duyuru",
        "KONTR Payına Dayalı Vadeli İşlem Sözleşmelerinde Yeni Vade Aylarının İşleme Açılmaması",
    ),
)
def test_acik_piyasa_kurali_regulasyon_bist_wide(title):
    html = HTML.replace(
        "BIST Geri Alım Endeksi Dönemsel Değişiklikleri",
        title,
        1,
    )
    result = parse_borsa_istanbul_announcement_html(html, source_url=URL)
    assert result.item.event_type is EventType.REGULASYON
    assert result.item.market_scope is MarketScope.BIST_WIDE


@pytest.mark.parametrize(
    "title",
    (
        "BIST Temettü ve BIST Temettü 25 Endeksleri Dönemsel Değişiklikleri",
        "BIST-KYD Fon Endeksleri Dönemsel Değişiklikleri",
        "Hesaplanmaya Başlayacak Yeni Sektör Endeksleri Hakkında Duyuru",
    ),
)
def test_endeks_duyurusu_diger_bist_wide(title):
    html = HTML.replace(
        "BIST Geri Alım Endeksi Dönemsel Değişiklikleri",
        title,
        1,
    )
    result = parse_borsa_istanbul_announcement_html(html, source_url=URL)
    assert result.item.event_type is EventType.DIGER
    assert result.item.market_scope is MarketScope.BIST_WIDE


@pytest.mark.parametrize(
    "title",
    (
        "Borsa İstanbul’da Gong Örnek Enerji İçin Çaldı",
        "Borsa İstanbul Yeni Veri Merkezini Devreye Alıyor",
        "Finansal Okuryazarlık Eğitim Programı",
    ),
)
def test_genel_kurumsal_duyuru_other(title):
    html = HTML.replace(
        "BIST Geri Alım Endeksi Dönemsel Değişiklikleri",
        title,
        1,
    )
    result = parse_borsa_istanbul_announcement_html(html, source_url=URL)
    assert result.item.event_type is EventType.DIGER
    assert result.item.market_scope is MarketScope.OTHER


def test_tarih_yoksa_reddedilir():
    html = HTML.replace("05.08.2026", "")
    with pytest.raises(BorsaIstanbulAdapterError, match="tarihi"):
        parse_borsa_istanbul_announcement_html(html, source_url=URL)


def test_gecersiz_tarih_reddedilir():
    html = HTML.replace("05.08.2026", "35.18.2026")
    with pytest.raises(BorsaIstanbulAdapterError, match="geçersiz"):
        parse_borsa_istanbul_announcement_html(html, source_url=URL)


def test_ag_varsayilan_kapali():
    adapter = BorsaIstanbulAnnouncementUrlAdapter()
    with pytest.raises(BorsaIstanbulAdapterError, match="ağ erişimi kapalı"):
        adapter.fetch(URL)


def test_acik_ag_injected_fetcher():
    calls = []

    def fetcher(url, timeout):
        calls.append((url, timeout))
        return HTML.encode("utf-8"), URL, "text/html; charset=utf-8"

    result = BorsaIstanbulAnnouncementUrlAdapter(
        network_enabled=True,
        fetcher=fetcher,
    ).fetch(URL)

    assert calls == [(URL, 10)]
    assert result.item.source_name == "Borsa İstanbul"


def test_redirect_farkli_host_reddedilir():
    def fetcher(url, timeout):
        return (
            HTML.encode(),
            "https://evil.example/duyuru/15547/test",
            "text/html",
        )

    with pytest.raises(BorsaIstanbulAdapterError, match="borsaistanbul.com"):
        BorsaIstanbulAnnouncementUrlAdapter(
            network_enabled=True,
            fetcher=fetcher,
        ).fetch(URL)


def test_redirect_farkli_duyuru_reddedilir():
    def fetcher(url, timeout):
        return (
            HTML.encode(),
            "https://www.borsaistanbul.com/duyuru/15548/baska-duyuru",
            "text/html",
        )

    with pytest.raises(BorsaIstanbulAdapterError, match="farklı bir duyuru"):
        BorsaIstanbulAnnouncementUrlAdapter(
            network_enabled=True,
            fetcher=fetcher,
        ).fetch(URL)


def test_html_disinda_yanit_reddedilir():
    def fetcher(url, timeout):
        return b"%PDF", URL, "application/pdf"

    with pytest.raises(BorsaIstanbulAdapterError, match="HTML değil"):
        BorsaIstanbulAnnouncementUrlAdapter(
            network_enabled=True,
            fetcher=fetcher,
        ).fetch(URL)


@pytest.mark.parametrize("timeout", (0, 31))
def test_timeout_siniri(timeout):
    with pytest.raises(ValueError, match="timeout_seconds"):
        BorsaIstanbulAnnouncementUrlAdapter(timeout_seconds=timeout)


def test_feed_ingestion_dry_run_ile_uyumlu(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_borsa_istanbul_announcement_html(HTML, source_url=URL).item

    preview = service.preview(item)

    assert preview.source.canonical_name == "Borsa İstanbul"
    assert preview.source.tier is SourceTier.TIER_1_OFFICIAL
    assert preview.duplicate is False
    assert archive.list_news() == ()


def test_acik_import_ile_borsa_duyurusu_arsivlenir(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_borsa_istanbul_announcement_html(HTML, source_url=URL).item

    result = service.import_item(item)

    assert result.archived is True
    saved = archive.list_news()[0]
    assert saved.source_name == "Borsa İstanbul"
    assert saved.source_tier is SourceTier.TIER_1_OFFICIAL
    event = archive.list_events()[0]
    assert event.market_scope is MarketScope.BIST_WIDE
    assert event.symbols == ()
    assert event.sectors == ()


def test_ikinci_import_duplicate(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_borsa_istanbul_announcement_html(HTML, source_url=URL).item

    assert service.import_item(item).archived is True
    second = service.import_item(item)

    assert second.archived is False
    assert second.duplicate is True
