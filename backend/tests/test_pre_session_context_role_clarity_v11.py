from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard.py"


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_seans_oncesi_baglam_v11_rolu_aciktir():
    text = source()
    assert "SEANS_ONCESI_BAGLAM_V11_ROLE_CLARITY" in text
    assert "Seans Öncesi Bağlam — Günlük Piyasa Hazırlığı" in text
    assert "işlenmiş günlük piyasa raporlarını ve arşivlenmiş AI değerlendirmesini" in text
    assert "Bugünün Önemli Gelişmeleri veya Ekonomik Takvim sekmelerinin yerine geçmez" in text
    assert "Yeni teknik skor, fiyat yönü, işlem sinyali veya AL/SAT kararı üretmez" in text


def test_seans_oncesi_baglam_v11_mevcut_routing_korunur():
    text = source()
    assert '"Seans Öncesi Bağlam"' in text
    assert "render_market_context_dashboard(" in text
    assert "project_root=Path(__file__).resolve().parents[1]" in text
    assert "Seans Öncesi Bağlam ekranında günlük raporları değerlendirin" in text
