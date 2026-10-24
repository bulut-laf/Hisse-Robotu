from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD_PATH = Path("backend/dashboard.py")


def _dashboard_source() -> str:
    return DASHBOARD_PATH.read_text(encoding="utf-8")


def _dashboard_ast() -> ast.Module:
    return ast.parse(_dashboard_source())


def test_dashboard_kap_vbts_durum_karti_fonksiyonu_var() -> None:
    tree = _dashboard_ast()

    functions = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    assert "kap_vbts_durum_karti_goster" in functions


def test_kap_vbts_durum_karti_gerekli_mesajlari_icerir() -> None:
    source = _dashboard_source()

    assert "VBTS veri kaynağı seçilmedi" in source
    assert "Toplu tarama kilitli" in source
    assert "Manuel VBTS koruması aktif" in source


def test_toplu_tarama_formu_durum_kartini_gosterir() -> None:
    tree = _dashboard_ast()

    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "kap_vbts_durum_karti_goster"
    ]

    assert len(calls) >= 1
