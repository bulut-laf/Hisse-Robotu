from pathlib import Path


DASHBOARD = Path("backend/app/ui/news_center_dashboard.py")
PANEL = Path("backend/app/ui/official_source_operations_panel.py")


def test_sprint176_basligi_var():
    assert "Sprint-176" in DASHBOARD.read_text(encoding="utf-8")


def test_operations_panel_dashboarda_bagli():
    text = DASHBOARD.read_text(encoding="utf-8")
    assert "render_official_source_operations_panel" in text
    assert "source_names=active_adapter_names" in text


def test_panel_ag_testi_olmadigini_aciklar():
    text = PANEL.read_text(encoding="utf-8")
    assert "Kaynaklara ping/GET atmaz" in text
    assert "otomatik sağlık testi yapmaz" in text


def test_panel_son_preview_archive_success_gosterir():
    text = PANEL.read_text(encoding="utf-8")
    assert '"Son önizleme"' in text
    assert '"Önizleme sonucu"' in text
    assert '"Son arşiv işlemi"' in text
    assert '"Arşiv sonucu"' in text
    assert '"Son başarılı kullanım"' in text


def test_panel_son_50_operasyonu_gosterir():
    assert "records[:50]" in PANEL.read_text(encoding="utf-8")


def test_panel_gecersiz_satir_uyarisi_var():
    text = PANEL.read_text(encoding="utf-8")
    assert '"Geçersiz satır"' in text
    assert "okunamayan satırlar var" in text


def test_panel_silme_butonu_yok():
    text = PANEL.read_text(encoding="utf-8")
    assert "sil" not in text.casefold()
    assert "delete" not in text.casefold()


def test_panel_streamlit_eski_api_kullanmaz():
    text = PANEL.read_text(encoding="utf-8")
    assert "use_container_width" not in text
    assert 'width="stretch"' in text


def test_dashboard_polling_yasagi_korunur():
    text = DASHBOARD.read_text(encoding="utf-8")
    assert "otomatik polling yapmaz" in text
    assert "toplu sorgu veya arka plan taraması yapmaz" in text


def test_mevcut_renderer_cagrisi_korunur():
    text = DASHBOARD.read_text(encoding="utf-8")
    assert "render_official_source_feed_blocks(st, archive, ISTANBUL)" in text
