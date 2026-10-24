from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard.py"


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_ai_analiz_asistani_v11_rolu_aciktir():
    text = source()
    assert "AI_ANALIZ_ASISTANI_V11_ROLE_CLARITY" in text
    assert "AI Analiz Asistanı bağımsız bir AL/SAT motoru değildir" in text
    assert "piyasa bağlamını özetler" in text
    assert "AI hisse sohbeti mevcut teknik analiz bağlamını açıklamaya yardımcı olur" in text
    assert "teknik teyit skorunu, işlem planını veya AL/SAT kararını değiştirmez" in text


def test_ai_analiz_asistani_v11_mevcut_safety_kontratlari_korur():
    text = source()
    assert "Günlük AI karar desteği" in text
    assert "Bu bölüm yeni AI çağrısı yapmaz" in text
    assert "Teknik skorları ve " in text
    assert "AL/SAT kararlarını değiştirmez." in text
    assert "AI Geçmişi ve Eğilim" in text
    assert "Yeni API çağrısı yapmaz; teknik skor ve AL/SAT kararlarına veri aktarmaz" in text
    assert "render_stock_ai_chat(st)" in text
