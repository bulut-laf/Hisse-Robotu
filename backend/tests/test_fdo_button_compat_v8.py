from pathlib import Path

UI = Path("backend/app/ui/fund_analysis_center.py")

def test_fdo_button_is_legacy_stub_compatible():
    text = UI.read_text(encoding="utf-8")
    assert "refresh_clicked = False" in text
    assert 'if hasattr(st, "button"):' in text
    assert "KAP FDO + Baskı Riskini Tam Güncelle" in text

def test_fdo_stays_before_profile():
    text = UI.read_text(encoding="utf-8")
    start = text.index("def render_fund_analysis_center(")
    body = text[start:]
    assert body.index("_render_fdo_pressure_production(") < body.index("_render_selected_fund_profile(")
