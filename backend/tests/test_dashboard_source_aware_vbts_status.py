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


def test_kap_vbts_durum_karti_kaynak_secimini_okur() -> None:
    source = _status_card_source()
    assert "HISSE_ROBOTU_VBTS_SOURCE" in source
    assert "manual_csv" in source


def test_kap_vbts_durum_karti_kaynak_yokken_uyari_verir() -> None:
    source = _status_card_source()
    assert "VBTS veri kaynağı seçilmedi" in source
    assert "Toplu tarama çalışır; VBTS tedbirleri doğrulanamaz." in source
    assert "Toplu tarama kilitli" not in source


def test_kap_vbts_durum_karti_manual_csv_durumlarini_icerir() -> None:
    source = _status_card_source()
    assert "Manuel VBTS kaynağı seçildi ancak CSV dosyası tanımlı değil" in source
    assert "Toplu tarama VBTS doğrulaması olmadan devam eder" in source
    assert "Manuel VBTS uyarı katmanı aktif" in source


def test_toplu_tarama_formu_kaynak_duyarli_karti_kullanmaya_devam_eder() -> None:
    calls = [
        node
        for node in ast.walk(_dashboard_ast())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "kap_vbts_durum_karti_goster"
    ]
    assert len(calls) >= 1
