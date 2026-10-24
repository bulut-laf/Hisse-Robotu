from pathlib import Path


UI = Path("backend/app/ui/news_center_dashboard.py")
RENDERER = Path("backend/app/ui/official_source_feed_renderer.py")


def source():
    return (
        UI.read_text(encoding="utf-8")
        + "\n"
        + RENDERER.read_text(encoding="utf-8")
    )


def test_spk_adapter_import_edilir():
    text = source()
    assert "from backend.app.news_center.spk_adapter import (" in text
    assert "SpkPressUrlAdapter" in text
    assert "SpkAdapterError" in text


def test_spk_url_alani_var():
    text = source()
    assert 'slug="spk"' in text
    assert 'return f"news_center_{self.slug}_feed_url"' in text
    assert "SPK basın duyurusu URL'si" in text


def test_spk_ag_onayi_varsayilan_kapali():
    text = source()
    assert "Bu işlem için SPK ağına bağlan" in text
    assert 'slug="spk"' in text
    assert 'return f"news_center_{self.slug}_network_enabled"' in text
    assert "value=False" in text


def test_spk_onizleme_ve_import_ayri():
    text = source()
    assert "SPK URL'sini önizle" in text
    assert "SPK önizlemesini arşive aktar" in text


def test_kap_tcmb_tuik_spk_adapterleri_aktif_kalmali():
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


def test_spk_piyasa_kapsami_uydurmama_metni_var():
    text = source()
    assert "piyasa kapsamı uydurulmaz" in text
