from pathlib import Path


UI = Path("backend/app/ui/news_center_dashboard.py")


def _source() -> str:
    return UI.read_text(encoding="utf-8")


def test_gun_sonu_modulu_import_edilir():
    source = _source()
    assert "from backend.app.news_center.day_end_summary import (" in source
    assert "build_day_end_summary" in source
    assert "day_end_development_rows" in source


def test_gun_sonu_sekmesi_var():
    source = _source()
    assert '"Gün Sonu Özeti"' in source
    assert "with day_end_tab:" in source


def test_gun_sonu_tarih_secimi_var():
    source = _source()
    assert "news_center_day_end_date" in source
    assert "Gün sonu tarihi" in source


def test_gun_sonu_metrikleri_var():
    source = _source()
    for label in (
        "Piyasa olayı",
        "Önem ≥80",
        "Gün içi haber",
        "KAP",
        "Hisse",
        "Sektör",
        "Portföy teması",
        "Takvim",
    ):
        assert label in source


def test_yeni_skor_ve_ai_yorumu_yasagi_acik():
    source = _source()
    assert "yeni bir birleşik skor üretmez" in source
    assert "AI yorumu üretmez" in source


def test_mevcut_sekmeler_korunur():
    source = _source()
    for label in (
        "Bugünün Önemli Gelişmeleri",
        "Ekonomik Takvim",
        "KAP Akışı",
        "Hisse Haberleri",
        "Sektör Etki Haritası",
        "Portföy Etki Radarı",
        "Haber Arşivi",
    ):
        assert f'"{label}"' in source
