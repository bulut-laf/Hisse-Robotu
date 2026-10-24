from pathlib import Path

UI = Path("backend/app/ui/news_center_dashboard.py")
RENDERER = Path("backend/app/ui/official_source_feed_renderer.py")

def source():
    return (
        UI.read_text(encoding="utf-8")
        + "\n"
        + RENDERER.read_text(encoding="utf-8")
    )

def test_hmb_adapter_import_edilir():
    text = source()
    assert "from backend.app.news_center.hmb_adapter import (" in text
    assert "HmbPressUrlAdapter" in text
    assert "HmbAdapterError" in text

def test_hmb_url_alani_var():
    text = source()
    assert 'slug="hmb"' in text
    assert 'return f"news_center_{self.slug}_feed_url"' in text
    assert "HMB basın duyurusu URL'si" in text

def test_hmb_ag_onayi_varsayilan_kapali():
    text = source()
    assert "Bu işlem için HMB ağına bağlan" in text
    assert 'slug="hmb"' in text
    assert 'return f"news_center_{self.slug}_network_enabled"' in text
    assert "value=False" in text

def test_hmb_onizleme_ve_import_ayri():
    text = source()
    assert "HMB URL'sini önizle" in text
    assert "HMB önizlemesini arşive aktar" in text

def test_kap_tcmb_tuik_spk_hmb_adapterleri_aktif_kalmali():
    text = source()
    assert "official_source_adapter_names" in text
    assert 'feed_source_statuses((*active_adapter_names,))' in text
    assert 'metric("Aktif adapter",' in text

def test_otomatik_polling_yok_mesaji_korunur():
    assert "otomatik polling yapmaz" in source()

def test_eski_streamlit_api_yok():
    text = source()
    assert "use_container_width" not in text
    assert 'width="stretch"' in text

def test_hmb_govdeden_piyasa_etkisi_tahmin_etmez_metni_var():
    assert "gövdeden piyasa etkisi tahmin edilmez" in source()
