from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard.py"


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_haftalik_performans_v11_rolu_aciktir():
    text = source()

    assert "HAFTALIK_PERFORMANS_V11_ROLE_CLARITY" in text
    assert '"Haftalık Performans Raporu — Gölge İşlem Sonuç Özeti"' in text
    assert "Gölge Portföy kayıtlarını seçilen 7/14/21/28 günlük dönem için toplulaştırır" in text
    assert "Sinyal Sonuçları 5/10/20 günlük ileri sinyal performansını ölçerken" in text
    assert "yeni sinyal, teknik skor veya AL/SAT kararı üretmez" in text
    assert "Mevcut haftalık rapor kontratında R-multiple metriği bulunmaz" in text


def test_haftalik_performans_v11_mevcut_kontratlari_korur():
    text = source()

    expected_items = (
        "Rapor bitiş tarihi",
        "Rapor dönemi",
        "Son {value} gün",
        "Açılan",
        "Kapanan",
        "Açık",
        "Kazanan",
        "Kaybeden",
        "Gerçekleşen K/Z",
        "Gerçekleşmemiş K/Z",
        "Ortalama getiri",
        "Haftalık özet",
        "Başarı karşılaştırmaları",
        "İşlem ayrıntıları",
        "Rapor arşivi",
        "Haftalık CSV indir",
        "Haftalık PDF indir",
        "Raporu arşivle",
        "Sinyal sınıfı",
        "Kalite skoru bandı",
        "Günlük/haftalık yön uyumu",
        "Piyasa rejimi",
        "Sektör",
        "MFE (%)",
        "MAE (%)",
    )
    for expected in expected_items:
        assert expected in text
