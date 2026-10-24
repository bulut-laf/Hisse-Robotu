from pathlib import Path


PANEL = Path("backend/app/ui/public_news_feed_panel.py")
DASHBOARD = Path("backend/app/ui/news_center_dashboard.py")


def test_sprint181_ai_ozet_arsivden_once_ayri_acik_kullanici_butonu_ile_baslar():
    source = PANEL.read_text(encoding="utf-8")
    summary_button = source.index("Yeni haberleri AI ile topluca özetle")
    archive_button = source.index("Yeni haberleri Haber Merkezi arşivine aktar")
    assert summary_button < archive_button
    assert 'st.button(\n            "Yeni haberleri AI ile topluca özetle"' in source
    assert "summarize_public_news(summary_inputs)" in source


def test_sprint181_ai_ozet_yalniz_yeni_haberleri_kullanir_ve_arsiv_yazmaz():
    source = PANEL.read_text(encoding="utf-8")
    assert "if not preview.duplicate" in source
    assert "_summary_inputs(previews)" in source
    assert "import_preview" in source
    assert "AI Toplu Haber Özeti" in source
    assert "teknik analiz skoru" in source.casefold()


def test_sprint181_performans_siniri_ve_tam_aktarim_hesabi_korunur():
    source = PANEL.read_text(encoding="utf-8")
    assert "_PREVIEW_RENDER_LIMIT = 20" in source
    assert "Performans için tabloda yalnız en yeni" in source
    assert "tamamı aktarım ve AI özet hesabında korunuyor" in source


def test_sprint181_dashboard_v1_guvenlik_sinirlarini_koruyarak_ai_ozeti_aciklar():
    source = DASHBOARD.read_text(encoding="utf-8")
    assert "Otomatik AI değerlendirmesi yapmaz" in source
    assert "Sprint-181 yalnız kullanıcı başlatmalı halka açık RSS toplu özetini" in source
    assert "teknik analiz skorlarını ve işlem karar motorunu" in source
    assert "otomatik polling" in source and "toplu scraping" in source
