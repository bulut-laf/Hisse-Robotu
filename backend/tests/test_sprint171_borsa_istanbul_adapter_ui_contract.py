from pathlib import Path


UI = Path("backend/app/ui/news_center_dashboard.py")
RENDERER = Path("backend/app/ui/official_source_feed_renderer.py")


def source():
    return (
        UI.read_text(encoding="utf-8")
        + "\n"
        + RENDERER.read_text(encoding="utf-8")
    )


def test_borsa_adapter_import_edilir():
    text = source()
    assert "from backend.app.news_center.borsa_istanbul_adapter import (" in text
    assert "BorsaIstanbulAnnouncementUrlAdapter" in text
    assert "BorsaIstanbulAdapterError" in text


def test_borsa_url_alani_var():
    text = source()
    assert 'slug="borsa_istanbul"' in text
    assert 'return f"news_center_{self.slug}_feed_url"' in text
    assert "Borsa İstanbul duyuru URL'si" in text


def test_borsa_ag_onayi_varsayilan_kapali():
    text = source()
    assert "Bu işlem için Borsa İstanbul ağına bağlan" in text
    assert 'slug="borsa_istanbul"' in text
    assert 'return f"news_center_{self.slug}_network_enabled"' in text
    assert "value=False" in text


def test_borsa_onizleme_ve_import_ayri():
    text = source()
    assert "Borsa İstanbul URL'sini önizle" in text
    assert "Borsa İstanbul önizlemesini arşive aktar" in text


def test_borsa_i̇stanbul_adapteri_aktif_kalmali():
    text = source()
    assert "official_source_adapter_names" in text
    assert 'metric("Aktif adapter",' in text
    assert 'metric("Aktif adapter",' in text


def test_otomatik_polling_yok_mesaji_korunur():
    assert "otomatik polling yapmaz" in source()


def test_ek_pdf_otomatik_takip_edilmez_metni_var():
    text = source()
    assert "ek/PDF/Excel bağlantılarını otomatik takip etmez" in text


def test_govdeden_hisse_ve_sektor_tahmini_yok_metni_var():
    text = source()
    assert "gövdeden hisse veya sektör tahmin edilmez" in text


def test_eski_streamlit_api_yok():
    text = source()
    assert "use_container_width" not in text
    assert 'width="stretch"' in text
