import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "backend/dashboard.py"

def _has_financial_intelligence_route(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not isinstance(node.left, ast.Name) or node.left.id != "analiz_modu":
            continue
        for comparator in node.comparators:
            if isinstance(comparator, ast.Constant) and comparator.value == "Finansal Zekâ Paneli":
                return True
    return False

def test_dashboard_financial_intelligence_route_contract():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    ast.parse(source)
    assert "Temel Analiz" in source
    assert "Finansal Zekâ Paneli" in source
    assert _has_financial_intelligence_route(source)

def test_dashboard_preserves_temel_analiz_and_financial_intelligence():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    assert "Temel Analiz" in source
    assert "Finansal Zekâ Paneli" in source
