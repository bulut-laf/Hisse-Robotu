from pathlib import Path


def test_dashboard_esik_onerilerini_tarihsel_karsilastirir():
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert "esik_onerilerini_tarihsel_dogrula(" in source
    assert '"Eşik önerilerinin tarihsel karşılaştırması"' in source
    assert "aynı tarihsel kalibrasyon" in source
    assert 'file_name="Hisse-Robotu-On-Yukselis-Esik-Dogrulamasi.csv"' in source
