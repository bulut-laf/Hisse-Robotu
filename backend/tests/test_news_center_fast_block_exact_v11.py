from pathlib import Path

UI = Path("backend/app/ui/news_center_dashboard.py")


def source() -> str:
    return UI.read_text(encoding="utf-8-sig")


def test_haber_merkezi_hizli_blok_v11_exact_seams():
    text = source()
    expected = (
        "BREAKING_STREAM_V11_ROLE_CLARITY",
        "Son Dakika Akışı — Hızlı Haber İzleme",
        "EOD_SUMMARY_V11_ROLE_CLARITY",
        "Gün Sonu Özeti — Günlük Haber/Olay Kapanışı",
        "EKONOMIK_TAKVIM_V11_ROLE_CLARITY",
        "Ekonomik Takvim — Planlı Makro Olay Takibi",
    )
    for item in expected:
        assert item in text


def test_haber_merkezi_hizli_blok_v11_existing_safety_contracts():
    text = source()
    expected = (
        "bir skor üretmez. Fiyat yönü, AL/SAT, teknik skor veya AI yorumu",
        "Sprint-162 gün sonu görünümü yeni bir birleşik skor üretmez.",
        "sistem beklentiden iyi/kötü veya fiyat yönü yorumu üretmez.",
    )
    for item in expected:
        assert item in text
