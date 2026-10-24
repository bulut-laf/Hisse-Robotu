from pathlib import Path

UI = Path("backend/app/ui/fund_analysis_center.py")


def test_fdo_pressure_renders_before_selected_fund_profile():
    text = UI.read_text(encoding="utf-8")
    render = text[text.index("def render_fund_analysis_center("):]
    assert render.index("_render_fdo_pressure_production") < render.index("_render_selected_fund_profile")


def test_fdo_button_and_safety_contract_still_present():
    text = UI.read_text(encoding="utf-8")
    assert "KAP FDO + Baskı Riskini Tam Güncelle" in text
    assert "AL/SAT authority: NONE" in text
    assert "network_enabled=True" in text
