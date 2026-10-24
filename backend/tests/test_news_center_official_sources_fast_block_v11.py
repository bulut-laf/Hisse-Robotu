from pathlib import Path

UI = Path("backend/app/ui/news_center_dashboard.py")


def source() -> str:
    return UI.read_text(encoding="utf-8-sig")


def test_official_sources_fast_block_v11_role_clarity():
    text = source()
    expected = (
        "RESMI_KAYNAK_OPERASYONLARI_V11_ROLE_CLARITY",
        "Resmî Kaynak Operasyonları — Kontrollü Kaynak Çalıştırma",
        "KAP_AKISI_V11_ROLE_CLARITY",
        "KAP Akışı — Şirket Bildirimleri ve Resmî Açıklamalar",
    )
    for item in expected:
        assert item in text


def test_official_sources_existing_contracts():
    text = source()
    expected = (
        "render_official_source_operations_panel(",
        "kap_tab",
        "KAP",
        "TCMB",
        "TÜİK",
        "SPK",
        "HMB",
        "BIST",
        "Resmî Gazete",
    )
    for item in expected:
        assert item in text
