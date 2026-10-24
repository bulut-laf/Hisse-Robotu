from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard.py"


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_kayip_guvenlik_v11_rolu_aciktir():
    text = source()
    assert "KAYIP_GUVENLIK_V11_ROLE_CLARITY" in text
    assert '"İşlem Kayıp Analizi ve Güvenlik Kilidi"' in text
    assert "İşlem Günlüğü kayıt deposudur" in text
    assert "Kayıp Analizi geçmiş zararların nedenlerini açıklar" in text
    assert "Güvenlik Kilidi ise yeni işlem teklifini" in text
    assert "kazanç garantisi veya alım önerisi değildir" in text


def test_kayip_guvenlik_v11_mevcut_kontratlari_korur():
    text = source()
    expected_items = (
        "İşlem başına azami risk (%)",
        "Minimum risk/getiri",
        "Azami pozisyon / sermaye (%)",
        "Günlük zarar kilidi (%)",
        "Haftalık zarar kilidi (%)",
        "Azami ardışık zarar",
        "Toplam işlem",
        "Kazanan / Kaybeden",
        "Net K/Z",
        "Başarı oranı",
        "Kâr faktörü",
        "İşlem başına beklenti",
        "Azami düşüş",
        "En uzun zarar serisi",
        "Günlük net sonuç",
        "Haftalık net sonuç",
        "Güncel ardışık zarar",
        "Geç giriş",
        "Kaybeden pozisyona ekleme",
        "Aşırı yükselmiş",
        "Yeni işlem sembolü",
        "Planlanan giriş",
        "Planlanan lot",
        "Stop-loss (0 = yok)",
        "Hedef fiyat (0 = yok)",
        "Güvenlik kontrolünü çalıştır",
        "İşlemi engelleyen nedenler",
        "Uyarılar",
    )
    for expected in expected_items:
        assert expected in text
