from pathlib import Path

UI = Path("backend/app/ui/news_center_dashboard.py")


def source() -> str:
    return UI.read_text(encoding="utf-8-sig")


def test_bugunun_onemli_gelismeleri_v11_rolu_aciktir():
    text = source()
    assert "BUGUNUN_ONEMLI_GELISMELERI_V11_ROLE_CLARITY" in text
    assert "Bugünün Önemli Gelişmeleri — Günlük Olay Öncelik Özeti" in text
    assert "mevcut 0–100 önem skoruna göre süzer ve önceliklendirir" in text
    assert "günlük haber/olay → mevcut önem skoru → etki bağlantıları → sektör/hisse/portföy teması → kullanıcı özeti" in text
    assert "Bu ekran yeni skor, fiyat yönü, teknik skor, AI değerlendirmesi veya AL/SAT kararı üretmez" in text


def test_bugunun_onemli_gelismeleri_v11_mevcut_ui_kontratlari_korunur():
    text = source()
    assert '"Bugünün Önemli Gelişmeleri"' in text
    assert "build_daily_developments_brief" in text
    assert '"Değerlendirme günü"' in text
    assert '"Asgari önem"' in text
