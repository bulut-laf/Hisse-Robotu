from pathlib import Path


UI = Path("backend/app/ui/news_center_dashboard.py")


def _source() -> str:
    return UI.read_text(encoding="utf-8-sig")


def test_hisse_haberleri_sekmesi_ve_motoru_var():
    source = _source()
    assert '"Hisse Haberleri"' in source
    assert "build_symbol_news_brief" in source
    assert "symbol_news_rows" in source


def test_hisse_haberleri_filtreleri_var():
    source = _source()
    assert '"Son 24 saat"' in source
    assert '"Son 3 gün"' in source
    assert '"Son 7 gün"' in source
    assert '"Tüm arşiv"' in source
    assert '"Hisse filtresi"' in source
    assert '"Yalnız Gölge Portföy"' in source


def test_hisse_haberleri_ozet_metrikleri_var():
    source = _source()
    assert '"Hisse"' in source
    assert '"Olay"' in source
    assert '"Önem ≥80"' in source
    assert '"Çok kaynaklı"' in source
    assert '"Birincil kaynak"' in source
    assert '"KAP içeren"' in source


def test_hisse_haberleri_sembol_uydurmaz_ve_islem_yorumu_yapmaz():
    source = _source()
    assert "haber metninden hisse sembolü çıkarılmaz" in source
    assert "fiyat yönü veya AL/SAT" in source
    assert "yeni bir skor üretmez" in source


def test_sprint160_ve_onceki_ana_sekmeler_korunur():
    source = _source()
    assert "Sprint-160" in source
    assert '"KAP Akışı"' in source
    assert '"Ekonomik Takvim"' in source
    assert '"Bugünün Önemli Gelişmeleri"' in source
    assert '"Sektör Etki Haritası"' in source
    assert '"Portföy Etki Radarı"' in source
