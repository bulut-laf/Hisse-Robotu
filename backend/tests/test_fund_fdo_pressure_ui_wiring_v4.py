from pathlib import Path

UI = Path("backend/app/ui/fund_analysis_center.py")


def src():
    return UI.read_text(encoding="utf-8")


def test_button_is_guarded_for_legacy_stubs():
    text = src()
    assert 'if hasattr(st, "button")' in text
    assert "refresh_clicked = False" in text


def test_fdo_pressure_turkish_ui_is_clean():
    text = src()
    assert "Fon/FDO & Baskı Riski" in text
    assert "KAP FDO + Baskı Riskini Tam Güncelle" in text
