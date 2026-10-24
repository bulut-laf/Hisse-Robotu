import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "backend/dashboard.py"


def test_dashboard_financial_intelligence_route_contract():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    ast.parse(source)
    assert "Temel Analiz" in source
    assert "Finansal Zekâ Paneli" in source
    assert re.search(r'analiz_modu\\s*==\\s*([\"\\'])Finansal Zekâ Paneli\\1', source)


def test_dashboard_preserves_temel_analiz_and_financial_intelligence():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    assert "Temel Analiz" in source
    assert "Finansal Zekâ Paneli" in source
