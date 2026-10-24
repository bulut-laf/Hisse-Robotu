from pathlib import Path


UI = Path("backend/app/ui/news_center_dashboard.py")
RENDERER = Path("backend/app/ui/official_source_feed_renderer.py")


def source():
    return (
        UI.read_text(encoding="utf-8")
        + "\n"
        + RENDERER.read_text(encoding="utf-8")
    )


def test_kap_adapter_import_edilir():
    text = source()
    assert "from backend.app.news_center.kap_adapter import (" in text
    assert "KapUrlAdapter" in text
    assert "KapAdapterError" in text


def test_kap_url_alani_var():
    text = source()
    assert 'slug="kap"' in text
    assert 'return f"news_center_{self.slug}_feed_url"' in text
    assert "KAP bildirim detay URL'si" in text


def test_ag_onayi_varsayilan_kapali():
    text = source()
    assert "Bu işlem için KAP ağına bağlan" in text
    assert 'slug="kap"' in text
    assert 'return f"news_center_{self.slug}_network_enabled"' in text
    assert "value=False" in text


def test_kap_onizleme_ve_import_ayri_dugmeler():
    text = source()
    assert "KAP URL'sini önizle" in text
    assert "Önizlemeyi arşive aktar" in text


def test_kap_adapteri_aktif_kalmali():
    text = source()
    assert 'feed_source_statuses((' in text
    assert '"KAP"' in text


def test_ag_durumu_kontrollu_yazilir():
    text = source()
    assert 'metric("Ağ erişimi", "İSTEK BAZLI")' in text
    assert "otomatik polling yapmaz" in text


def test_tab_bloklari_fonksiyon_icinde():
    text = source()
    assert "\nwith feed_tab:" not in text
    assert "\nwith last_minute_tab:" not in text
    assert "\nwith news_tab:" not in text

def test_eski_streamlit_use_container_width_kullanilmaz():
    text = source()
    assert "use_container_width" not in text
    assert 'width="stretch"' in text
