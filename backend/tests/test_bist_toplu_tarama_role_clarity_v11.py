from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard.py"


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_bist_toplu_tarama_v11_rolu_aciktir():
    text = source()
    assert "BIST_TOPLU_TARAMA_V11_ROLE_CLARITY" in text
    assert '"BIST Toplu Tarama — Genel Teknik Aday Havuzu"' in text
    assert "Fırsat Radarı doğrulanmış haftalık/aylık profil eşleşmelerini öne çıkarır" in text
    assert "genel teknik aday havuzu üretir" in text
    assert "Güncel Teknik Analiz veya AL-SAT ile derinleştirilir" in text


def test_bist_toplu_tarama_v11_mevcut_kontratlari_korur():
    text = source()
    expected_items = (
        "BIST 30",
        "BIST 100",
        "BIST 500",
        "BIST Tüm",
        "Özel Liste",
        "Özel hisse listesi",
        "Tarama profili",
        "Temel kalite filtresini kullan",
        "VBTS",
        "Sektör bağlamı",
        "AL-SAT'a Gönder",
        "Toplu taramayı başlat",
    )
    for expected in expected_items:
        assert expected in text
