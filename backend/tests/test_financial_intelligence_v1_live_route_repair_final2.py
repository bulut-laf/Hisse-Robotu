import ast
from pathlib import Path

def _has_financial_intelligence_route(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "analiz_modu":
            if any(isinstance(c, ast.Constant) and c.value == "Finansal Zekâ Paneli" for c in node.comparators):
                return True
    return False

def test_financial_intelligence_live_route_current_contract():
    root = Path(__file__).resolve().parents[2]
    dashboard = root / "backend/dashboard.py"
    text = dashboard.read_text(encoding="utf-8-sig")
    ast.parse(text)
    assert "Temel Analiz" in text
    assert "Finansal Zekâ Paneli" in text
    assert _has_financial_intelligence_route(text)
