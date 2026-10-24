from pathlib import Path


UI = Path("backend/app/ui/news_center_dashboard.py")


def _source() -> str:
    return UI.read_text(encoding="utf-8")


def test_son_dakika_modulu_import_edilir():
    source = _source()
    assert "from backend.app.news_center.last_minute import (" in source
    assert "build_last_minute_feed" in source
    assert "last_minute_rows" in source


def test_son_dakika_sekmesi_var():
    source = _source()
    assert '"Son Dakika"' in source
    assert "with last_minute_tab:" in source


def test_zaman_filtreleri_var():
    source = _source()
    for label in ("Son 1 saat", "Son 3 saat", "Son 6 saat", "Son 24 saat", "Son 3 gün", "Tüm arşiv"):
        assert label in source


def test_guvenilir_kaynak_varsayilan_acik():
    source = _source()
    assert "Yalnız güvenilir kaynaklar" in source
    assert "value=True" in source


def test_kaynak_hisse_portfoy_filtreleri_var():
    source = _source()
    assert "news_center_last_minute_source" in source
    assert "news_center_last_minute_symbol" in source
    assert "news_center_last_minute_portfolio_only" in source


def test_son_dakika_metrikleri_var():
    source = _source()
    for label in ("Haber", "Olay", "Birincil", "KAP", "Hisse bağlantılı", "Portföy teması"):
        assert label in source


def test_otomatik_internet_ve_yeni_skor_yasagi_acik():
    source = _source()
    assert "otomatik internet akışı değildir" in source
    assert "yeni bir skor üretmez" in source
    assert "AI yorumu üretmez" in source


def test_mevcut_ana_sekmeler_korunur():
    source = _source()
    for label in (
        "Bugünün Önemli Gelişmeleri",
        "Gün Sonu Özeti",
        "Ekonomik Takvim",
        "KAP Akışı",
        "Hisse Haberleri",
        "Sektör Etki Haritası",
        "Portföy Etki Radarı",
        "Haber Arşivi",
    ):
        assert f'"{label}"' in source
