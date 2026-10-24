from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def test_sprint42_vbts_paneli_dashboarda_eklendi() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    assert "dashboard_vbts_manager import" in source
    assert "def vbts_yonetim_paneli_goster() -> None:" in source
    assert "Yeni VBTS kaydı ekle" in source
    assert "Seçili VBTS kaydını sil" in source


def test_toplu_tarama_paneli_cagiriyor() -> None:
    tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "vbts_yonetim_paneli_goster"
    ]
    assert calls
