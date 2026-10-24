from pathlib import Path

UI = Path("backend/app/ui/fund_analysis_center.py")

def source():
    return UI.read_text(encoding="utf-8")

def test_fdo_pressure_section_is_wired():
    text = source()
    assert "def _render_fdo_pressure_production(" in text
    assert "KAP FDO + Baskı Riskini Tam Güncelle" in text
    assert "populate_kap_free_float_for_symbols(" in text
    assert "build_fund_pressure_read_model(" in text
    assert "fund_pressure_rows(profiles, inputs)" in text

def test_fdo_pressure_preserves_safety_contract():
    text = source()
    assert "network_enabled=True" in text
    assert "default_free_float_store()" in text
    assert "MAX_FDO_SYMBOLS_PER_REFRESH" in text
    assert "otomatik AL/SAT yetkisi yoktur" in text
