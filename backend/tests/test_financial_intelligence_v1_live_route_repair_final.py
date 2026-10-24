from pathlib import Path
import re


def test_financial_intelligence_route_final():
    root = Path(__file__).resolve().parents[2]
    dashboard = root / "backend/dashboard.py"
    text = dashboard.read_text(encoding="utf-8-sig")

    assert "Temel Analiz" in text
    assert "Finansal Zekâ Paneli" in text
    assert re.search(r'analiz_modu\s*==\s*["\']Finansal Zekâ Paneli["\']', text)
    assert "financial_intelligence_dashboard" in text
