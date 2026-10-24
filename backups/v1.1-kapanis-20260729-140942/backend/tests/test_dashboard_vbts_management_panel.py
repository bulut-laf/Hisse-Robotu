from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def _source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_dashboard_vbts_manager_importlari_var() -> None:
    source = _source()
    assert "dashboard_vbts_manager import" in source
    assert "add_vbts_record" in source
    assert "delete_vbts_record" in source


def test_vbts_yonetim_paneli_ekleme_ve_silme_icerir() -> None:
    source = _source()
    assert "def vbts_yonetim_paneli_goster() -> None:" in source
    assert "Yeni VBTS kaydı ekle" in source
    assert "Seçili VBTS kaydını sil" in source
    assert "Resmî KAP bildirimiyle doğruladım" in source


def test_toplu_tarama_formu_vbts_yonetim_panelini_cagirir() -> None:
    tree = ast.parse(_source())
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "vbts_yonetim_paneli_goster"
    ]
    assert calls
