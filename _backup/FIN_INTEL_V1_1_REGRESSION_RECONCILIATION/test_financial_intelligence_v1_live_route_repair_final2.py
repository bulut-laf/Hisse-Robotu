from pathlib import Path
import re


def test_financial_intelligence_route_final2():
    root = Path(__file__).resolve().parents[2]
    dashboard = root / "backend/dashboard.py"
    text = dashboard.read_text(encoding="utf-8-sig")

    assert "Temel Analiz" in text
    assert "Finansal Zekâ Paneli" in text
    assert re.search(r'analiz_modu\s*==\s*(["\'])Finansal Zekâ Paneli\1', text)
    assert "from app.ui import financial_intelligence_dashboard as _fin_intel_ui" in text
    assert "_fin_intel_ui." in text
