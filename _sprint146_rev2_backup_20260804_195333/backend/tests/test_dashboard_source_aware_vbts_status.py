from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD_PATH = Path("backend/dashboard.py")


def _dashboard_source() -> str:
    return DASHBOARD_PATH.read_text(encoding="utf-8")


def _dashboard_ast() -> ast.Module:
    return ast.parse(_dashboard_source())


def test_kap_vbts_durum_karti_kaynak_secimini_okur() -> None:
    source = _dashboard_source()

    assert "HISSE_ROBOTU_VBTS_SOURCE" in source
    assert "manual_csv" in source


def test_kap_vbts_durum_karti_kaynak_yokken_dogru_mesaji_icerir() -> None:
    source = _dashboard_source()

    assert "VBTS veri kaynağı seçilmedi" in source
    assert "Toplu tarama kilitli" in source


def test_kap_vbts_durum_karti_manual_csv_durumlarini_icerir() -> None:
    source = _dashboard_source()

    assert "Manuel VBTS kaynağı seçildi" in source
    assert "CSV dosyası tanımlı değil" in source
    assert "Manuel VBTS koruması aktif" in source


def test_toplu_tarama_formu_kaynak_duyarli_karti_kullanmaya_devam_eder() -> None:
    tree = _dashboard_ast()

    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "kap_vbts_durum_karti_goster"
    ]

    assert len(calls) >= 1
