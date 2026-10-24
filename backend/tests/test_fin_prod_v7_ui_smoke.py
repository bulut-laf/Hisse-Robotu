import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "backend/dashboard.py"

def _has_financial_intelligence_route(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "analiz_modu":
            if any(isinstance(c, ast.Constant) and c.value == "Finansal Zekâ Paneli" for c in node.comparators):
                return True
    return False

def test_active_dashboard_contains_financial_intelligence_route():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    ast.parse(source)
    assert "Finansal Zekâ Paneli" in source
    assert _has_financial_intelligence_route(source)
