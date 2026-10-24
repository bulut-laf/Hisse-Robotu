from pathlib import Path


def test_dashboard_esik_onerilerini_karar_destegi_olarak_gosterir() -> None:
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert "kalibrasyon_esik_onerilerini_hesapla(" in source
    assert '"Kalibrasyona dayalı eşik önerileri"' in source
    assert "üretim motoruna otomatik uygulanmaz" in source
    assert 'file_name="Hisse-Robotu-On-Yukselis-Esik-Onerileri.csv"' in source
