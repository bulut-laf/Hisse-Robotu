from pathlib import Path


def test_dashboard_halka_acik_haber_panelini_kaynak_beslemeye_baglar():
    source = Path("backend/app/ui/news_center_dashboard.py").read_text(encoding="utf-8")
    assert "render_public_news_feed_panel" in source
    assert "render_public_news_feed_panel(st, archive, ISTANBUL)" in source
    assert '"Kaynak Besleme"' in source


def test_public_haber_paneli_tek_tikla_toplu_rss_onizleme_sunar():
    source = Path("backend/app/ui/public_news_feed_panel.py").read_text(encoding="utf-8")
    assert "Halka Açık Haber Akışı — V1.1" in source
    assert "Halka açık akışları önizle" in source
    assert "Yeni haberleri Haber Merkezi arşivine aktar" in source
    assert "Arka plan polling" in source
    assert "YOK" in source


def test_public_haber_cekirdegi_toplu_scraping_yapmaz():
    source = Path("backend/app/news_center/public_news_feed.py").read_text(encoding="utf-8")
    assert "urlopen" in source
    assert "PUBLIC_NEWS_MAX_RESPONSE_BYTES" in source
    assert "PUBLIC_NEWS_FEEDS" in source
    assert "beautifulsoup" not in source.casefold()


def test_public_haber_paneli_onizleme_tablosunu_performans_icin_sinirlar():
    source = Path("backend/app/ui/public_news_feed_panel.py").read_text(encoding="utf-8")
    assert "_PREVIEW_RENDER_LIMIT = 20" in source
    assert "preview_many" in source
    assert "import_preview" in source
    assert "Performans için tabloda yalnız en yeni" in source
