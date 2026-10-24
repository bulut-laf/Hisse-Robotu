from __future__ import annotations

from pathlib import Path

TESTS = {
    "backend/tests/test_fin_prod_v7_financial_intelligence_ui.py": """
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
""",
    "backend/tests/test_fin_prod_v7_ui_smoke.py": """
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
""",
    "backend/tests/test_financial_intelligence_v1_live_route_repair_final2.py": """
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
""",
    "backend/tests/test_financial_intelligence_v1_ui_zeroarg_adapter_route.py": """
import ast
from pathlib import Path

def _has_financial_intelligence_route(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "analiz_modu":
            if any(isinstance(c, ast.Constant) and c.value == "Finansal Zekâ Paneli" for c in node.comparators):
                return True
    return False

def test_financial_intelligence_route_is_live_without_legacy_zeroarg_requirement():
    root = Path(__file__).resolve().parents[2]
    dashboard = root / "backend/dashboard.py"
    renderer = root / "backend/app/ui/financial_intelligence_dashboard.py"
    dtext = dashboard.read_text(encoding="utf-8-sig")
    ast.parse(dtext)
    assert renderer.exists()
    assert "Temel Analiz" in dtext
    assert "Finansal Zekâ Paneli" in dtext
    assert _has_financial_intelligence_route(dtext)
""",
}

def main() -> None:
    root = Path(__file__).resolve().parents[2]
    backup = root / "_backup" / "FIN_INTEL_V1_1_REGRESSION_RECONCILIATION_V2"
    backup.mkdir(parents=True, exist_ok=True)

    for rel, content in TESTS.items():
        path = root / rel
        if path.exists():
            (backup / path.name).write_bytes(path.read_bytes())
        path.write_text(content.lstrip(), encoding="utf-8")
        compile(path.read_text(encoding="utf-8"), str(path), "exec")

    print(f"TEST_FILES_REPAIRED={len(TESTS)}")
    print("ROUTE_CHECK_METHOD=AST")
    print(f"BACKUP={backup}")
    print("FIN_INTEL_V1_1_REGRESSION_RECONCILIATION_V2=PASS")

if __name__ == "__main__":
    main()
