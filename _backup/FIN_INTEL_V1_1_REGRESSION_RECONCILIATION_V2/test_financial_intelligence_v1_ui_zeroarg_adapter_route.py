import ast
import re
from pathlib import Path


def test_financial_intelligence_route_is_live_without_legacy_zeroarg_requirement():
    root = Path(__file__).resolve().parents[2]
    dashboard = root / "backend/dashboard.py"
    renderer = root / "backend/app/ui/financial_intelligence_dashboard.py"

    dtext = dashboard.read_text(encoding="utf-8-sig")
    ast.parse(dtext)

    assert renderer.exists()
    assert "Temel Analiz" in dtext
    assert "Finansal Zekâ Paneli" in dtext
    assert re.search(r'analiz_modu\\s*==\\s*([\"\\'])Finansal Zekâ Paneli\\1', dtext)
