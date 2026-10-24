from pathlib import Path


DASHBOARD = Path("backend/app/ui/news_center_dashboard.py")
RENDERER = Path("backend/app/ui/official_source_feed_renderer.py")


def test_sprint175_dashboard_renderer_importu_var():
    text = DASHBOARD.read_text(encoding="utf-8")
    assert "from backend.app.ui.official_source_feed_renderer import (" in text
    assert "render_official_source_feed_blocks" in text


def test_sprint175_basligi_var():
    assert "Sprint-175" in DASHBOARD.read_text(encoding="utf-8")


def test_yedi_kaynak_basligi_rendererda_korunur():
    text = RENDERER.read_text(encoding="utf-8")
    for title in (
        "KAP — kontrollü bildirim URL'si",
        "TCMB — kontrollü basın duyurusu URL'si",
        "TÜİK — kontrollü haber bülteni URL'si",
        "SPK — kontrollü basın duyurusu URL'si",
        "HMB — kontrollü basın duyurusu URL'si",
        "Borsa İstanbul — kontrollü duyuru URL'si",
        "Resmî Gazete — kontrollü HTML mevzuat URL'si",
    ):
        assert title in text


def test_polling_ve_arka_plan_tarama_acilmadi():
    text = DASHBOARD.read_text(encoding="utf-8")
    assert "otomatik polling yapmaz" in text
    assert "toplu sorgu veya arka plan taraması yapmaz" in text


def test_health_paneli_korunur():
    text = DASHBOARD.read_text(encoding="utf-8")
    assert 'st.subheader("Resmî adapter yapısal sağlığı")' in text
    assert "diagnose_official_source_adapters()" in text


def test_renderer_dry_run_ve_acik_arsiv_onayini_korur():
    text = RENDERER.read_text(encoding="utf-8")
    assert "Dry-run başarılı. Henüz arşive yazılmadı." in text
    assert "disabled=preview.duplicate" in text
    assert "import_item(preview_item)" in text


def test_renderer_url_degistirilirse_yeniden_preview_ister():
    text = RENDERER.read_text(encoding="utf-8")
    assert "url_changed_message" in text
    assert "Arşive aktarmadan önce" in text


def test_eski_streamlit_api_yok():
    text = DASHBOARD.read_text(encoding="utf-8") + RENDERER.read_text(encoding="utf-8")
    assert "use_container_width" not in text
    assert 'width="stretch"' in text
