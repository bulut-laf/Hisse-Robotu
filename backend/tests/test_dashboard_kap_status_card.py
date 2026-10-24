from __future__ import annotations

import ast
from pathlib import Path

DASHBOARD_PATH = Path("backend/dashboard.py")


def _dashboard_source() -> str:
    return DASHBOARD_PATH.read_text(encoding="utf-8")


def _dashboard_ast() -> ast.Module:
    return ast.parse(_dashboard_source())


def _status_card_source() -> str:
    source = _dashboard_source()
    start = source.index("def kap_vbts_durum_karti_goster")
    end = source.index("\ndef temel_skor_deposu", start)
    return source[start:end]


def test_dashboard_kap_vbts_durum_karti_fonksiyonu_var() -> None:
    functions = {
        node.name
        for node in _dashboard_ast().body
        if isinstance(node, ast.FunctionDef)
    }
    assert "kap_vbts_durum_karti_goster" in functions


def test_kap_vbts_durum_karti_uyari_modu_mesajlarini_icerir() -> None:
    source = _status_card_source()
    assert "VBTS veri kaynağı seçilmedi" in source
    assert "Toplu tarama çalışır" in source
    assert "Manuel VBTS uyarı katmanı aktif" in source
    assert "Toplu tarama kilitli" not in source


def test_toplu_tarama_formu_durum_kartini_gosterir() -> None:
    calls = [
        node
        for node in ast.walk(_dashboard_ast())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "kap_vbts_durum_karti_goster"
    ]
    assert len(calls) >= 1
