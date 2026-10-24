from __future__ import annotations

import ast
from pathlib import Path

DASHBOARD_PATH = Path("backend/dashboard.py")


def _dashboard_ast() -> ast.Module:
    return ast.parse(DASHBOARD_PATH.read_text(encoding="utf-8"))


def test_dashboard_vbts_kaynak_fabrikasini_import_eder() -> None:
    imported_names: set[str] = set()
    for node in ast.walk(_dashboard_ast()):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module == "backend.app.compliance.dashboard_market_scanner_source_factory":
            imported_names.update(alias.name for alias in node.names)
    assert "build_dashboard_market_scanner" in imported_names


def test_dashboard_toplu_taramada_dogrudan_servis_olusturmaz() -> None:
    direct_calls = [
        node
        for node in ast.walk(_dashboard_ast())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "BistMarketScannerService"
    ]
    assert direct_calls == []


def test_dashboard_toplu_taramada_vbts_kaynak_fabrikasini_soft_modda_kullanir() -> None:
    calls = [
        node
        for node in ast.walk(_dashboard_ast())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "build_dashboard_market_scanner"
    ]
    assert len(calls) >= 1
    assert any(
        any(
            keyword.arg == "vbts_hard_block"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is False
            for keyword in call.keywords
        )
        for call in calls
    )
