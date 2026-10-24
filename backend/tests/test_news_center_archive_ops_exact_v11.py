from pathlib import Path

UI = Path("backend/app/ui/news_center_dashboard.py")


def source() -> str:
    return UI.read_text(encoding="utf-8-sig")


def test_haber_merkezi_arsiv_ops_exact_v11_role_clarity():
    text = source()
    expected = (
        "GUNLUK_HABER_OPERASYONU_V11_ROLE_CLARITY",
        "Günlük Haber Operasyonu — Sistem ve Görev Akışı",
        "KAYNAK_BESLEME_V11_ROLE_CLARITY",
        "Kaynak Besleme — Haber Toplama ve Veri Girişi",
        "HABER_ARSIVI_V11_ROLE_CLARITY",
        "Haber Arşivi — Filtreli Geçmiş Olay İncelemesi",
    )
    for item in expected:
        assert item in text


def test_haber_merkezi_arsiv_ops_existing_contracts():
    text = source()
    expected = (
        "render_daily_news_operations_panel(",
        "render_official_source_operations_panel(",
        "render_public_news_feed_panel(",
        "build_archive_news_view(",
        '"Arşivde ara"',
        '"Asgari önem"',
        '"Yalnız güvenilir kaynaklar"',
        '"Hisse"',
        '"Sektör"',
        '"Olay türü"',
        '"Piyasa kapsamı"',
    )
    for item in expected:
        assert item in text
