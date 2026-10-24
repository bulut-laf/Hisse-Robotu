from pathlib import Path
import re


def test_financial_intelligence_live_route_is_wired():
    root = Path(__file__).resolve().parents[2]
    dashboard = root / "backend/dashboard.py"
    renderer = root / "backend/app/ui/financial_intelligence_dashboard.py"

    dtext = dashboard.read_text(encoding="utf-8-sig")
    rtext = renderer.read_text(encoding="utf-8-sig")

    assert "Finansal Zekâ Paneli" in dtext
    assert re.search(r'analiz_modu\s*==\s*["\']Finansal Zekâ Paneli["\']', dtext)
    assert "financial_intelligence_dashboard" in dtext
    assert "Temel Analiz" in dtext
    assert rtext.strip()
