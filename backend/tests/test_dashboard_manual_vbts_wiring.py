from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD_PATH = Path("backend/dashboard.py")


def _dashboard_ast() -> ast.Module:
    source = DASHBOARD_PATH.read_text(encoding="utf-8")
    return ast.parse(source)


def test_dashboard_yeni_vbts_kaynak_fabrikasini_import_eder() -> None:
    tree = _dashboard_ast()

    imported_names: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue

        if (
            node.module
            == "backend.app.compliance.dashboard_market_scanner_source_factory"
        ):
            imported_names.update(alias.name for alias in node.names)

    assert "build_dashboard_market_scanner" in imported_names
    assert "DashboardMarketScannerSourceError" in imported_names


def test_dashboard_eski_kap_tarama_fabrikasini_kullanmaz() -> None:
    tree = _dashboard_ast()

    old_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "build_protected_market_scanner"
    ]

    assert old_calls == []


def test_dashboard_toplu_taramada_yeni_kaynak_fabrikasini_kullanir() -> None:
    tree = _dashboard_ast()

    new_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "build_dashboard_market_scanner"
    ]

    assert len(new_calls) >= 1
