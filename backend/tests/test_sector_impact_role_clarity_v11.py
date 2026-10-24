from pathlib import Path

UI = Path("backend/app/ui/news_center_dashboard.py")


def source() -> str:
    return UI.read_text(encoding="utf-8-sig")


def test_sektor_etki_haritasi_v11_rolu_aciktir():
    text = source()
    assert "SEKTOR_ETKI_HARITASI_V11_ROLE_CLARITY" in text
    assert "Sektör Etki Haritası — Haber/Olay Sektör Bağlantıları" in text
    assert "doğrudan sektör olaylarını ve duyarlılık ilişkilerini ayrı gösterir" in text
    assert "Akış: Haber/Olay → sektör bağlantısı ve gerekçesi → Sektör Etki Haritası → ilgili hisse/Portföy Etki Radarı" in text
    assert "Harita fiyat yönü, AL/SAT kararı, teknik skor veya AI kararı üretmez" in text
