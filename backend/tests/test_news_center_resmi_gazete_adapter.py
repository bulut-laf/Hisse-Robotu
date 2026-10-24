from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.archive import NewsArchive
from backend.app.news_center.feed_ingestion import FeedIngestionService
from backend.app.news_center.models import EventType, MarketScope, SourceTier
from backend.app.news_center.resmi_gazete_adapter import (
    ResmiGazeteAdapterError,
    ResmiGazeteArticleUrlAdapter,
    parse_resmi_gazete_article_html,
    validate_resmi_gazete_article_url,
)


IST = ZoneInfo("Europe/Istanbul")
URL = "https://www.resmigazete.gov.tr/eskiler/2026/05/20260501-1.htm"

BASE_TITLE = (
    "7578 SOSYAL HİZMETLER KANUNU VE BAZI KANUNLARDA DEĞİŞİKLİK "
    "YAPILMASINA DAİR KANUN"
)

HTML = f"""
<html>
<head><title>Resmî Gazete</title></head>
<body>
<b>1 Mayıs 2026 CUMA</b>
<b>Resmî Gazete</b>
<b>Sayı : 33240</b>
<p><b>{BASE_TITLE}</b></p>
<p>MADDE 1- Bu Kanunun amacı sosyal hizmetlere ilişkin düzenlemeler yapmaktır.</p>
<p>MADDE 2- İlgili hükümler değiştirilmiştir.</p>
</body>
</html>
"""


def _with_title(title: str) -> str:
    return HTML.replace(BASE_TITLE, title)


def test_resmi_gazete_url_dogrulanir():
    value, article_id, published_at = validate_resmi_gazete_article_url(URL)
    assert value == URL
    assert article_id == "20260501-1"
    assert published_at == datetime(2026, 5, 1, 0, 0, tzinfo=IST)


@pytest.mark.parametrize(
    "url",
    (
        "http://www.resmigazete.gov.tr/eskiler/2026/05/20260501-1.htm",
        "https://evil.example/eskiler/2026/05/20260501-1.htm",
        "https://www.resmigazete.gov.tr/eskiler/2026/05/20260501.htm",
        "https://www.resmigazete.gov.tr/eskiler/2026/05/20260501.pdf",
        "https://www.resmigazete.gov.tr/eskiler/2026/05/20260501-1.pdf",
        "https://www.resmigazete.gov.tr/eskiler/2026/04/20260501-1.htm",
        "https://www.resmigazete.gov.tr/eskiler/2026/05/20260501-1.htm?x=1",
        "https://user@www.resmigazete.gov.tr/eskiler/2026/05/20260501-1.htm",
    ),
)
def test_guvensiz_veya_kapsam_disi_url_reddedilir(url):
    with pytest.raises(ResmiGazeteAdapterError):
        validate_resmi_gazete_article_url(url)


def test_gecersiz_url_tarihi_reddedilir():
    with pytest.raises(ResmiGazeteAdapterError, match="tarih geçersiz"):
        validate_resmi_gazete_article_url(
            "https://www.resmigazete.gov.tr/eskiler/2026/02/20260231-1.htm"
        )


def test_html_feed_item_uretir():
    result = parse_resmi_gazete_article_html(HTML, source_url=URL)
    item = result.item

    assert result.article_id == "20260501-1"
    assert item.source_name == "Resmî Gazete"
    assert item.external_id == "20260501-1"
    assert item.published_at == datetime(2026, 5, 1, 0, 0, tzinfo=IST)
    assert item.headline.startswith("7578 SOSYAL HİZMETLER KANUNU")
    assert item.event_type is EventType.REGULASYON
    assert item.market_scope is MarketScope.OTHER
    assert item.symbols == ()
    assert item.sectors == ()


def test_govde_mevzuat_metninden_gelir():
    result = parse_resmi_gazete_article_html(HTML, source_url=URL)
    assert "MADDE 1" in result.item.body
    assert "MADDE 2" in result.item.body


def test_script_icerigi_govdeye_girmez():
    html = HTML.replace(
        "</body>",
        "<script>THYAO gizli içerik</script></body>",
    )
    result = parse_resmi_gazete_article_html(html, source_url=URL)
    assert "gizli içerik" not in result.item.body


def test_hisse_ve_sektor_tahmini_yok():
    html = HTML.replace(
        "İlgili hükümler değiştirilmiştir.",
        "İlgili hükümler değiştirilmiştir. THYAO ASELS Bankacılık.",
    )
    result = parse_resmi_gazete_article_html(html, source_url=URL)
    assert result.item.symbols == ()
    assert result.item.sectors == ()


def test_sermaye_piyasasi_regulasyon_bist_wide():
    html = _with_title("SERMAYE PİYASASI KANUNUNDA DEĞİŞİKLİK YAPILMASINA DAİR KANUN")
    result = parse_resmi_gazete_article_html(html, source_url=URL)
    assert result.item.event_type is EventType.REGULASYON
    assert result.item.market_scope is MarketScope.BIST_WIDE


def test_kambiyo_doviz_turkey_macro():
    html = _with_title("TÜRK PARASI KIYMETİNİ KORUMA HAKKINDA KAMBİYO TEBLİĞİ")
    result = parse_resmi_gazete_article_html(html, source_url=URL)
    assert result.item.event_type is EventType.DOVIZ
    assert result.item.market_scope is MarketScope.TURKEY_MACRO


def test_borclanma_turkey_macro():
    html = _with_title("DEVLET İÇ BORÇLANMA SENETLERİ HAKKINDA TEBLİĞ")
    result = parse_resmi_gazete_article_html(html, source_url=URL)
    assert result.item.event_type is EventType.BORCLANMA_FINANSMAN
    assert result.item.market_scope is MarketScope.TURKEY_MACRO


def test_enflasyon_turkey_macro():
    html = _with_title("FİYAT İSTİKRARI HAKKINDA YÖNETMELİK")
    result = parse_resmi_gazete_article_html(html, source_url=URL)
    assert result.item.event_type is EventType.ENFLASYON
    assert result.item.market_scope is MarketScope.TURKEY_MACRO


@pytest.mark.parametrize(
    "title",
    (
        "KATMA DEĞER VERGİSİ GENEL UYGULAMA TEBLİĞİNDE DEĞİŞİKLİK",
        "ÖZEL TÜKETİM VERGİSİ UYGULAMA TEBLİĞİ",
        "BANKACILIK DÜZENLEMELERİ HAKKINDA YÖNETMELİK",
        "MERKEZİ YÖNETİM BÜTÇE UYGULAMA TEBLİĞİ",
    ),
)
def test_mali_finansal_duzenleme_turkey_macro(title):
    html = _with_title(title)
    result = parse_resmi_gazete_article_html(html, source_url=URL)
    assert result.item.event_type is EventType.REGULASYON
    assert result.item.market_scope is MarketScope.TURKEY_MACRO


def test_mevzuat_niteligi_acik_degilse_diger_other():
    html = _with_title("KAMU KURUMUNDAN DUYURU")
    result = parse_resmi_gazete_article_html(html, source_url=URL)
    assert result.item.event_type is EventType.DIGER
    assert result.item.market_scope is MarketScope.OTHER


def test_ag_varsayilan_kapali():
    adapter = ResmiGazeteArticleUrlAdapter()
    with pytest.raises(ResmiGazeteAdapterError, match="ağ erişimi kapalı"):
        adapter.fetch(URL)


def test_acik_ag_injected_fetcher():
    calls = []

    def fetcher(url, timeout):
        calls.append((url, timeout))
        return HTML.encode("utf-8"), URL, "text/html; charset=utf-8"

    result = ResmiGazeteArticleUrlAdapter(
        network_enabled=True,
        fetcher=fetcher,
    ).fetch(URL)

    assert calls == [(URL, 10)]
    assert result.item.source_name == "Resmî Gazete"


def test_redirect_farkli_host_reddedilir():
    def fetcher(url, timeout):
        return (
            HTML.encode(),
            "https://evil.example/eskiler/2026/05/20260501-1.htm",
            "text/html",
        )

    with pytest.raises(ResmiGazeteAdapterError, match="resmigazete.gov.tr"):
        ResmiGazeteArticleUrlAdapter(
            network_enabled=True,
            fetcher=fetcher,
        ).fetch(URL)


def test_redirect_farkli_madde_reddedilir():
    def fetcher(url, timeout):
        return (
            HTML.encode(),
            "https://www.resmigazete.gov.tr/eskiler/2026/05/20260501-2.htm",
            "text/html",
        )

    with pytest.raises(ResmiGazeteAdapterError, match="farklı bir mevzuat"):
        ResmiGazeteArticleUrlAdapter(
            network_enabled=True,
            fetcher=fetcher,
        ).fetch(URL)


def test_html_disinda_yanit_reddedilir():
    def fetcher(url, timeout):
        return b"%PDF", URL, "application/pdf"

    with pytest.raises(ResmiGazeteAdapterError, match="HTML değil"):
        ResmiGazeteArticleUrlAdapter(
            network_enabled=True,
            fetcher=fetcher,
        ).fetch(URL)


@pytest.mark.parametrize("timeout", (0, 31))
def test_timeout_siniri(timeout):
    with pytest.raises(ValueError, match="timeout_seconds"):
        ResmiGazeteArticleUrlAdapter(timeout_seconds=timeout)


def test_feed_ingestion_dry_run_ile_uyumlu(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_resmi_gazete_article_html(HTML, source_url=URL).item

    preview = service.preview(item)

    assert preview.source.canonical_name == "Resmî Gazete"
    assert preview.source.tier is SourceTier.TIER_1_OFFICIAL
    assert preview.duplicate is False
    assert archive.list_news() == ()


def test_acik_import_ile_resmi_gazete_arsivlenir(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_resmi_gazete_article_html(HTML, source_url=URL).item

    result = service.import_item(item)

    assert result.archived is True
    saved = archive.list_news()[0]
    assert saved.source_name == "Resmî Gazete"
    assert saved.source_tier is SourceTier.TIER_1_OFFICIAL
    event = archive.list_events()[0]
    assert event.event_type is EventType.REGULASYON
    assert event.market_scope is MarketScope.OTHER
    assert event.symbols == ()
    assert event.sectors == ()


def test_ikinci_import_duplicate(tmp_path: Path):
    archive = NewsArchive(tmp_path / "news.sqlite3")
    service = FeedIngestionService(archive)
    item = parse_resmi_gazete_article_html(HTML, source_url=URL).item

    assert service.import_item(item).archived is True
    second = service.import_item(item)

    assert second.archived is False
    assert second.duplicate is True
