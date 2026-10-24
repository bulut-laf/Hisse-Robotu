from pathlib import Path

def test_dashboard_gercek_sonuc_degerlendirmesini_icerir():
    source=Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert '"Gerçek Sonuç Değerlendirmesi"' in source
    assert "gercek_sonuclari_degerlendir(" in source
    assert '"Varsayılan / kalibre eşik karşılaştırması"' in source
