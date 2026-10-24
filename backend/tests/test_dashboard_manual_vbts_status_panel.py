from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD_PATH = Path("backend/dashboard.py")


def _dashboard_source() -> str:
    return DASHBOARD_PATH.read_text(encoding="utf-8")


def _dashboard_ast() -> ast.Module:
    return ast.parse(_dashboard_source())


def test_dashboard_manual_vbts_durum_paneli_fonksiyonu_var() -> None:
    tree = _dashboard_ast()

    functions = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    assert "manuel_vbts_durum_paneli_goster" in functions


def test_manual_vbts_durum_paneli_dosya_ve_guncellik_bilgisi_icerir() -> None:
    source = _dashboard_source()

    assert "VBTS CSV dosyası" in source
    assert "Son güncelleme" in source
    assert "Kayıt sayısı" in source


def test_toplu_tarama_formu_manual_vbts_durum_panelini_gosterir() -> None:
    tree = _dashboard_ast()

    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "manuel_vbts_durum_paneli_goster"
    ]

    assert len(calls) >= 1
