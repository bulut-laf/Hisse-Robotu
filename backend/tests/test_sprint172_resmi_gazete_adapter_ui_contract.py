from pathlib import Path


UI = Path("backend/app/ui/news_center_dashboard.py")
RENDERER = Path("backend/app/ui/official_source_feed_renderer.py")


def source():
    return (
        UI.read_text(encoding="utf-8")
        + "\n"
        + RENDERER.read_text(encoding="utf-8")
    )


def test_resmi_gazete_adapter_import_edilir():
    text = source()
    assert "from backend.app.news_center.resmi_gazete_adapter import (" in text
    assert "ResmiGazeteArticleUrlAdapter" in text
    assert "ResmiGazeteAdapterError" in text


def test_resmi_gazete_url_alani_var():
    text = source()
    assert 'slug="resmi_gazete"' in text
    assert 'return f"news_center_{self.slug}_feed_url"' in text
    assert "Resmî Gazete mevzuat URL'si" in text


def test_resmi_gazete_ag_onayi_varsayilan_kapali():
    text = source()
    assert "Bu işlem için Resmî Gazete ağına bağlan" in text
    assert 'slug="resmi_gazete"' in text
    assert 'return f"news_center_{self.slug}_network_enabled"' in text
    assert "value=False" in text


def test_resmi_gazete_onizleme_ve_import_ayri():
    text = source()
    assert "Resmî Gazete URL'sini önizle" in text
    assert "Resmî Gazete önizlemesini arşive aktar" in text


def test_resmi_gazete_adapteri_aktif_kalmali():
    text = source()
    assert "official_source_adapter_names" in text
    assert 'metric("Aktif adapter",' in text


def test_pdf_ve_sayi_indeksi_otomatik_takip_edilmez():
    text = source()
    assert "PDF/ek veya günlük sayı indeksini otomatik " in text
    assert "takip etmez." in text


def test_govdeden_piyasa_etkisi_tahmini_yok():
    text = source()
    assert "gövdeden piyasa kapsamı, hisse veya sektör " in text
    assert "tahmin edilmez." in text


def test_otomatik_polling_yok_mesaji_korunur():
    assert "otomatik polling yapmaz" in source()


def test_eski_streamlit_api_yok():
    text = source()
    assert "use_container_width" not in text
    assert 'width="stretch"' in text
