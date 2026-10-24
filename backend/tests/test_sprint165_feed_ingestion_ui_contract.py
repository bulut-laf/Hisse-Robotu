from pathlib import Path

UI = Path("backend/app/ui/news_center_dashboard.py")


def source():
    return UI.read_text(encoding="utf-8")


def test_feed_ingestion_import_edilir():
    text = source()
    assert "from backend.app.news_center.feed_ingestion import (" in text
    assert "feed_source_statuses" in text


def test_kaynak_besleme_sekmesi_var():
    text = source()
    assert '"Kaynak Besleme"' in text
    assert "with feed_tab:" in text


def test_ag_erisim_kontrollu_oldugu_acikca_yazilir():
    text = source()
    assert "Ağ erişimi" in text
    assert "otomatik polling" in text


def test_adapter_sayaci_gosterilir():
    text = source()
    assert 'metric("Aktif adapter",' in text


def test_mimari_sinirlar_korunur():
    text = source()
    assert "dry-run →" in text
    assert "açık onay → arşiv" in text
    assert "Yeni skor, fiyat yönü, AL/SAT veya AI yorumu üretmez" in text


def test_tab_bloklari_render_fonksiyonu_disina_tasmamis():
    text = source()
    assert "\nwith last_minute_tab:" not in text
    assert "\nwith day_end_tab:" not in text
    assert "\nwith news_tab:" not in text
