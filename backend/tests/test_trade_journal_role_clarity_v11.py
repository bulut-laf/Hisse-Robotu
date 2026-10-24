from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard.py"


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_islem_gunlugu_v11_rolu_aciktir():
    text = source()
    assert "ISLEM_GUNLUGU_V11_ROLE_CLARITY" in text
    assert "KAYIP_GUVENLIK_V11_ROLE_CLARITY" in text
    assert '"İşlem Kayıp Analizi ve Güvenlik Kilidi"' in text
    assert '"#### İşlem günlüğü ve güvenlik akışı"' in text
    assert "tamamlanmış gerçek/deneme işlemlerini" in text
    assert "Gölge Portföy açık/kapalı kağıt pozisyonları yönetir" in text
    assert "Haftalık Performans Raporu dönemsel gölge performansını özetler" in text
    assert "gerçekleşen R" in text


def test_islem_gunlugu_v11_mevcut_kontratlari_korur():
    text = source()
    expected_items = (
        "Tamamlanmış işlem ekle",
        "Hesap türü",
        "Hisse sembolü",
        "Giriş tarihi",
        "Çıkış tarihi",
        "Giriş fiyatı",
        "Çıkış fiyatı",
        "Lot",
        "İşlem anındaki sermaye",
        "Planlanan stop (0 = yok)",
        "Planlanan hedef (0 = yok)",
        "Toplam komisyon/masraf",
        "Sinyal sınıfı",
        "Girişin geç yapıldığını düşünüyorum",
        "Kaybeden pozisyona ekleme yapıldı",
        "Aşırı yükselmiş bölgede giriş yapıldı",
        "Notlar",
        "İşlemi günlüğe kaydet",
        "CSV şablonunu indir",
        "Mevcut günlüğü CSV olarak indir",
        "CSV kayıtlarını günlüğe ekle",
        "Yeni işlem ön kontrolü",
        "Güvenlik kontrolünü çalıştır",
    )
    for expected in expected_items:
        assert expected in text
