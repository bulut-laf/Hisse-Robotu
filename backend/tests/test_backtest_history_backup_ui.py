from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD_DOSYASI = Path(__file__).resolve().parents[1] / "dashboard.py"


def _tree() -> ast.Module:
    return ast.parse(DASHBOARD_DOSYASI.read_text(encoding="utf-8"))


def _calls(name: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == name
    ]


def _strings() -> set[str]:
    return {
        node.value
        for node in ast.walk(_tree())
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_yedekleme_bolumu_zip_indirme_sunar() -> None:
    strings = _strings()

    assert "Yedekleme ve geri yükleme" in strings
    assert "Yedeklenecek kayıtlar" in strings
    assert "Seçili kayıtları ZIP olarak yedekle" in strings
    assert _calls("download_button")


def test_geri_yukleme_zip_dosyasi_kabul_eder() -> None:
    strings = _strings()

    assert "Analiz geçmişi ZIP yedeği" in strings
    assert _calls("file_uploader")


def test_geri_yukleme_onay_ve_devre_disi_dugme_kullanir() -> None:
    strings = _strings()
    restore_buttons = [
        call
        for call in _calls("button")
        if call.args
        and isinstance(call.args[0], ast.Constant)
        and call.args[0].value == "Yedeği geri yükle"
    ]

    assert (
        "Yedekteki yeni kayıtların analiz geçmişine eklenmesini onaylıyorum."
        in strings
    )
    assert len(restore_buttons) == 1
    keywords = {keyword.arg for keyword in restore_buttons[0].keywords}
    assert "disabled" in keywords
    assert "width" in keywords


def test_geri_yukleme_bos_gecmiste_de_gosterilir() -> None:
    source = DASHBOARD_DOSYASI.read_text(encoding="utf-8")

    backup_call = source.index("gecmis_yedekleme_goster(depo, kayitlar)")
    empty_check = source.index("if not kayitlar:", backup_call)
    assert backup_call < empty_check
