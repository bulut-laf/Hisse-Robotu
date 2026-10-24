from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD_DOSYASI = Path(__file__).resolve().parents[1] / "dashboard.py"


def _agac() -> ast.Module:
    return ast.parse(DASHBOARD_DOSYASI.read_text(encoding="utf-8"))


def _cagrilar(ad: str) -> list[ast.Call]:
    return [
        dugum
        for dugum in ast.walk(_agac())
        if isinstance(dugum, ast.Call)
        and isinstance(dugum.func, ast.Attribute)
        and dugum.func.attr == ad
    ]


def _sabit_metinler() -> set[str]:
    return {
        dugum.value
        for dugum in ast.walk(_agac())
        if isinstance(dugum, ast.Constant) and isinstance(dugum.value, str)
    }


def test_gecmis_yonetimi_secili_kayitlari_coklu_sectirir() -> None:
    metinler = _sabit_metinler()

    assert "Geçmiş yönetimi" in metinler
    assert "Silinecek kayıtlar" in metinler
    assert _cagrilar("multiselect")


def test_silme_iki_asamali_acik_onay_ister() -> None:
    metinler = _sabit_metinler()

    assert "Seçili kayıtların kalıcı olarak silineceğini anlıyorum." in metinler
    assert "Onaylamak için SİL yazın" in metinler
    assert _cagrilar("checkbox")
    assert _cagrilar("text_input")


def test_silme_dugmesi_guvenli_bicimde_devre_disi_baslar() -> None:
    silme_dugmeleri = [
        cagri
        for cagri in _cagrilar("button")
        if cagri.args
        and isinstance(cagri.args[0], ast.Constant)
        and cagri.args[0].value == "Seçili kayıtları kalıcı olarak sil"
    ]

    assert len(silme_dugmeleri) == 1
    anahtarlar = {keyword.arg for keyword in silme_dugmeleri[0].keywords}
    assert "disabled" in anahtarlar
    assert "width" in anahtarlar


def test_basarili_silme_sonrasi_arayuz_yenilenir() -> None:
    assert _cagrilar("rerun")
