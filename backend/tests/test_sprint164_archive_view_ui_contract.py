from pathlib import Path


UI = Path("backend/app/ui/news_center_dashboard.py")


def _source():
    return UI.read_text(encoding="utf-8")


def test_archive_view_import_edilir():
    source = _source()
    assert "from backend.app.news_center.archive_view import (" in source
    assert "build_archive_news_view" in source
    assert "archive_news_rows" in source


def test_haber_arsivi_gelismis_filtreler_var():
    source = _source()
    for token in (
        "news_center_archive_start_date",
        "news_center_archive_end_date",
        "news_center_archive_source",
        "news_center_archive_symbol",
        "news_center_archive_sector",
        "news_center_archive_event_type",
        "news_center_archive_scope",
        "news_center_archive_min_importance",
        "news_center_archive_text_query",
    ):
        assert token in source


def test_arsiv_tam_liste_limitleri_genisletildi():
    source = _source()
    assert "archive.list_news(limit=10000)" in source
    assert "archive.list_events(limit=5000)" in source


def test_arsiv_metrikleri_var():
    source = _source()
    for label in ("Haber", "Olay", "Kaynak", "Birincil", "KAP", "Hisse bağlantılı"):
        assert f'"{label}"' in source


def test_arsiv_mimari_sinir_acik():
    source = _source()
    assert "haber metninden hisse veya sektör tahmin etmez" in source
    assert "yeni skor, fiyat yönü, AL/SAT veya AI yorumu üretmez" in source


def test_mevcut_haber_arsivi_sekmesi_korunur():
    assert '"Haber Arşivi"' in _source()
