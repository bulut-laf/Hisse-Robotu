import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "backend/dashboard.py"


def test_active_dashboard_contains_financial_intelligence_route():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    ast.parse(source)
    assert "Finansal Zekâ Paneli" in source
    assert re.search(r'analiz_modu\\s*==\\s*([\"\\'])Finansal Zekâ Paneli\\1', source)
