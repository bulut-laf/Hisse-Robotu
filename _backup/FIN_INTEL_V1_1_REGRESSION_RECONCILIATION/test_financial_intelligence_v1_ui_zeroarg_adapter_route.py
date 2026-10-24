from pathlib import Path
import ast

def test_financial_intelligence_zeroarg_adapter_and_route():
    root = Path(__file__).resolve().parents[2]
    dashboard = root / "backend/dashboard.py"
    renderer = root / "backend/app/ui/financial_intelligence_dashboard.py"

    dtext = dashboard.read_text(encoding="utf-8-sig")
    rtext = renderer.read_text(encoding="utf-8-sig")

    assert "Temel Analiz" in dtext
    assert "Finansal Zekâ Paneli" in dtext
    assert "render_financial_intelligence_panel_entry()" in dtext
    assert "from app.ui.financial_intelligence_dashboard import render_financial_intelligence_panel_entry" in dtext

    tree = ast.parse(rtext)
    adapters = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "render_financial_intelligence_panel_entry"]
    assert len(adapters) == 1
    assert len(adapters[0].args.args) == 0
