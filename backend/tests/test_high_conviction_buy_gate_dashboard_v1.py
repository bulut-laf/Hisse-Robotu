from pathlib import Path


def test_dashboard_wires_high_conviction_gate():
    text = Path("backend/dashboard.py").read_text(encoding="utf-8")
    assert "HIGH_CONVICTION_BUY_GATE_V1" in text
    assert "build_high_conviction_buy_gate" in text
    assert "Yüksek Güvenli AL" in text
    assert "yeni birleşik güven skoru üretmez" in text
