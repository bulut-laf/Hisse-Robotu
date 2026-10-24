from pathlib import Path

UI = Path("backend/app/ui/news_center_dashboard.py")


def _source() -> str:
    return UI.read_text(encoding="utf-8-sig")


def test_ekonomik_takvim_sekmesi_var():
    source = _source()
    assert '"Ekonomik Takvim"' in source
    assert "EconomicCalendarStore" in source


def test_manual_takvim_kaydi_ve_sonuc_guncelleme_var():
    source = _source()
    assert '"Takvim olayını kaydet"' in source
    assert '"Takvim değerlerini güncelle"' in source
    assert "create_calendar_entry" in source
    assert "update_values" in source


def test_degerler_ham_metin_ve_yon_yorumu_yok():
    source = _source()
    assert "ham metin olarak saklanır" in source
    assert "beklentiden iyi/kötü" in source
    assert "fiyat yönü yorumu üretmez" in source


def test_sprint158_ve_mevcut_haber_sekmeleri_korunur():
    source = _source()
    assert "Sprint-158" in source
    assert '"Bugünün Önemli Gelişmeleri"' in source
    assert '"Sektör Etki Haritası"' in source
    assert '"Portföy Etki Radarı"' in source
