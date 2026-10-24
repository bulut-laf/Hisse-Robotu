from pathlib import Path
import ast

UI = Path("backend/app/ui/fund_analysis_center.py")

def test_fdo_renders_before_selected_fund_profile():
    text = UI.read_text(encoding="utf-8")
    tree = ast.parse(text)
    render = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "render_fund_analysis_center"
    )
    calls = {}
    for node in ast.walk(render):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Name):
                if func.id in {"_render_selected_fund_profile", "_render_fdo_pressure_production"}:
                    calls[func.id] = node.lineno
    assert calls["_render_fdo_pressure_production"] < calls["_render_selected_fund_profile"]
