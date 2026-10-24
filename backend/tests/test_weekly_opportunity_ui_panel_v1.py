from __future__ import annotations

import ast
from pathlib import Path

UI = Path("backend/app/ui/prebreakout_dashboard.py")

def _dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _dotted(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return ""

def test_weekly_panel_marker_and_imports_present():
    source = UI.read_text(encoding="utf-8")
    assert "WEEKLY_OPPORTUNITY_UI_PANEL_V1" in source
    assert "list_weekly_snapshot_records" in source
    assert "load_weekly_snapshot" in source
    assert "weekly_opportunity_rows" in source

def test_weekly_panel_is_direct_surface_in_prebreakout_form():
    source = UI.read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(
        n for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name == "on_yukselis_hazirlik_formu"
    )
    direct = []
    for stmt in fn.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            direct.append(_dotted(stmt.value.func).split(".")[-1])
    assert "_render_weekly_opportunity_panel" in direct

def test_zero_snapshot_state_is_visible():
    source = UI.read_text(encoding="utf-8")
    assert "İlk Cuma canonical Weekly snapshot henüz oluşmadı" in source
    assert 'metric("W4", 0)' in source
    assert 'metric("Pilot", 0)' in source

def test_weekly_panel_is_read_only():
    source = UI.read_text(encoding="utf-8")
    tree = ast.parse(source)
    helper = next(
        n for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name == "_render_weekly_opportunity_panel"
    )
    helper_src = ast.get_source_segment(source, helper) or ""
    assert "persist_weekly_snapshot" not in helper_src
    assert "settle_weekly_outcomes" not in helper_src
    assert "BistMarketScannerService" not in helper_src
    assert "AL / BEKLE / PAS" in helper_src
