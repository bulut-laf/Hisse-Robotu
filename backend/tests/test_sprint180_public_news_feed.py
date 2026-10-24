from datetime import timezone

import pytest

from backend.app.news_center.models import EventType, MarketScope, SourceTier
from backend.app.news_center.public_news_feed import (
    PUBLIC_NEWS_FEEDS,
    PublicNewsFeedError,
    parse_public_news_feed,
)
from backend.app.news_center.source_registry import resolve_source


RSS = b'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Ekonomi</title>
<item>
<title>BIST 100 endeksi gune yukselisle basladi</title>
<link>https://www.trthaber.com/haber/ekonomi/ornek-1.html</link>
<description><![CDATA[<p>Borsa Istanbul'da BIST 100 endeksi acilista yukselis kaydetti.</p>]]></description>
<pubDate>Mon, 10 Aug 2026 07:05:00 +0300</pubDate>
<guid>trt-1</guid>
</item>
<item>
<title>Petrol fiyatlari geriledi</title>
<link>https://www.trthaber.com/haber/ekonomi/ornek-2.html</link>
<description>Brent petrol fiyatlari geriledi.</description>
<pubDate>Mon, 10 Aug 2026 06:50:00 +0300</pubDate>
<guid>trt-2</guid>
</item>
</channel></rss>'''


def _trt_spec():
    return next(item for item in PUBLIC_NEWS_FEEDS if item.slug == "trt_ekonomi")


def test_aa_ve_trt_beyaz_listede_dogrulanmis_kaynaktir():
    aa = resolve_source("Anadolu Ajansı")
    trt = resolve_source("", "https://www.trthaber.com/ekonomi")
    assert aa is not None and aa.tier is SourceTier.OTHER_VERIFIED
    assert trt is not None and trt.canonical_name == "TRT Haber"
    assert trt.tier is SourceTier.OTHER_VERIFIED


def test_rss_kayitlari_feed_item_olarak_normalize_edilir():
    items = parse_public_news_feed(_trt_spec(), RSS)
    assert len(items) == 2
    assert items[0].source_name == "TRT Haber"
    assert items[0].published_at.tzinfo is not None
    assert items[0].published_at.utcoffset() is not None
    assert "<p>" not in items[0].body
    assert items[0].external_id == "trt-1"


def test_bist_haberi_deterministik_kapsam_onerisi_alir():
    item = parse_public_news_feed(_trt_spec(), RSS)[0]
    assert item.market_scope is MarketScope.BIST_WIDE
    assert item.event_type is EventType.DIGER
    assert item.symbols == ()


def test_petrol_haberi_emtia_olarak_siniflanir():
    item = parse_public_news_feed(_trt_spec(), RSS)[1]
    assert item.event_type is EventType.EMTIA


def test_rss_dis_domain_linki_otomatik_kabul_edilmez():
    body = RSS.replace(
        b"https://www.trthaber.com/haber/ekonomi/ornek-1.html",
        b"https://example.com/haber.html",
    )
    items = parse_public_news_feed(_trt_spec(), body)
    assert len(items) == 1
    assert items[0].external_id == "trt-2"


def test_bozuk_xml_acik_hata_verir():
    with pytest.raises(PublicNewsFeedError, match="RSS/XML"):
        parse_public_news_feed(_trt_spec(), b"<rss><bozuk>")


def test_kayitli_kanallar_sabit_https_ve_izinli_host_kullanir():
    assert {item.slug for item in PUBLIC_NEWS_FEEDS} == {
        "aa_ekonomi",
        "trt_ekonomi",
        "trt_son_dakika",
    }
    assert all(item.feed_url.startswith("https://") for item in PUBLIC_NEWS_FEEDS)
