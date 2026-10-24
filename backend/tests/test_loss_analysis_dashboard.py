from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard.py"


def test_islem_kayip_analizi_ana_menuye_ve_yonlendirmeye_eklenmistir() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")

    assert '"İşlem Kayıp Analizi"' in source
    assert 'elif analiz_modu == "İşlem Kayıp Analizi":' in source
    assert "islem_kayip_analizi_formu()" in source


def test_kayip_analizi_csv_ve_guvenlik_ekranlarini_icerir() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]

    assert "file_uploader" in calls
    assert "download_button" in calls
    assert "tabs" in calls
    assert "evaluate_trade_safety" in source
    assert "analyze_trade_losses" in source
