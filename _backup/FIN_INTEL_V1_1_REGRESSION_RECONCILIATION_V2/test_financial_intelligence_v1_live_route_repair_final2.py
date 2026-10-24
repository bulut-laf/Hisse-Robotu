import ast
import re
from pathlib import Path


def test_financial_intelligence_live_route_current_contract():
    root = Path(__file__).resolve().parents[2]
    dashboard = root / "backend/dashboard.py"
    text = dashboard.read_text(encoding="utf-8-sig")

    ast.parse(text)
    assert "Temel Analiz" in text
    assert "Finansal Zekâ Paneli" in text
    assert re.search(r'analiz_modu\\s*==\\s*([\"\\'])Finansal Zekâ Paneli\\1', text)
