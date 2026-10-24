from __future__ import annotations

from pathlib import Path

DASHBOARD = Path("backend/dashboard.py")


def _source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_vbts_ekleme_dugmesi_form_icinde_pasif_birakilmaz() -> None:
    assert "disabled=not resmi_onay" not in _source()


def test_resmi_kap_onayi_gonderim_sirasinda_dogrulanir() -> None:
    source = _source()
    assert "if not resmi_onay:" in source
    assert "VBTS kaydı eklemek için resmî KAP bildirimiyle" in source


def test_vbts_ekleme_dugmesi_mevcut() -> None:
    source = _source()
    assert '"VBTS kaydını ekle"' in source
    assert "st.form_submit_button" in source
