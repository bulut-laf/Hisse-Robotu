from pathlib import Path

def test_dashboard_canli_performans_karsilastirmasini_icerir():
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert "performans_karsilastirmasini_hesapla(" in source
    assert '"Canlı performans karşılaştırması"' in source
    assert '"Performans karşılaştırmasını CSV indir"' in source
