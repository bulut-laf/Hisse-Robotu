from pathlib import Path

UI = Path("backend/app/ui/news_center_dashboard.py")


def source() -> str:
    return UI.read_text(encoding="utf-8-sig")


def test_news_center_quality_core_fast_block_v11():
    text = source()
    expected = (
        "GUVENILIR_KAYNAKLAR_V11_ROLE_CLARITY",
        "Güvenilir Kaynaklar — Kaynak Kalitesi ve İzlenebilirlik",
        "COKLU_KAYNAK_BIRLESTIRME_V11_ROLE_CLARITY",
        "Çoklu Kaynak / Birleştirme — Aynı Olayı Tek Bağlamda Toplama",
        "ETIKET_BAGLANTI_V11_ROLE_CLARITY",
        "Etiket ve Bağlantılar — Olayı Hisse/Sektör Bağlamına Taşıma",
    )
    for item in expected:
        assert item in text
