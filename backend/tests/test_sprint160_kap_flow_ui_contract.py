from pathlib import Path


UI = Path("backend/app/ui/news_center_dashboard.py")


def _source() -> str:
    return UI.read_text(encoding="utf-8-sig")


def test_kap_akisi_sekmesi_ve_motoru_var():
    source = _source()
    assert '"KAP Akışı"' in source
    assert "build_kap_flow" in source
    assert "kap_flow_rows" in source


def test_kap_filtreleri_var():
    source = _source()
    assert '"Son 24 saat"' in source
    assert '"Son 3 gün"' in source
    assert '"Son 7 gün"' in source
    assert '"Tüm arşiv"' in source
    assert '"Hisse filtresi"' in source
    assert '"Yalnız Gölge Portföy"' in source


def test_kap_ozet_metrikleri_var():
    source = _source()
    assert '"KAP bildirimi"' in source
    assert '"Portföy teması"' in source
    assert '"Sembolsüz"' in source


def test_kap_otomatik_internet_ve_islem_yorumu_yapmaz():
    source = _source()
    assert "Otomatik KAP internet entegrasyonu" in source
    assert "fiyat yönü/AL-SAT yorumu" in source
    assert "sembolü uydurulmaz" in source


def test_sprint159_ve_onceki_ana_sekmeler_korunur():
    source = _source()
    assert "Sprint-159" in source
    assert '"Ekonomik Takvim"' in source
    assert '"Bugünün Önemli Gelişmeleri"' in source
    assert '"Sektör Etki Haritası"' in source
    assert '"Portföy Etki Radarı"' in source
