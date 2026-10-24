from pathlib import Path


def test_dashboard_shows_operational_closeout_contract():
    source = Path("backend/dashboard.py").read_text(encoding="utf-8")
    assert "Operasyonel Kapanış — Günlük Karar Zinciri" in source
    assert "build_operational_closeout()" in source
    assert "operational_closeout_rows" in source
    assert "Eksik halkalar:" in source
