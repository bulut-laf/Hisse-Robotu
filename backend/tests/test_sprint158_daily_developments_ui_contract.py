from pathlib import Path


UI = Path("backend/app/ui/news_center_dashboard.py")


def _source() -> str:
    return UI.read_text(encoding="utf-8-sig")


def test_bugunun_onemli_gelismeleri_sekmesi_var():
    source = _source()
    assert '"Bugünün Önemli Gelişmeleri"' in source
    assert "build_daily_developments_brief" in source


def test_gun_ve_onem_esigi_kullanici_tarafindan_secilir():
    source = _source()
    assert '"Değerlendirme günü"' in source
    assert '"Asgari önem"' in source


def test_ekran_yeni_skor_ve_fiyat_yonu_uretmedigini_aciklar():
    source = _source()
    assert "yeni bir skor üretmez" in source
    assert "Fiyat yönü veya AL/SAT kararı değildir" in source


def test_sprint156_ve_portfoy_radar_sozlesmeleri_korunur():
    source = _source()
    assert "Sprint-156" in source
    assert '"Sektör Etki Haritası"' in source
    assert '"Portföy Etki Radarı"' in source
