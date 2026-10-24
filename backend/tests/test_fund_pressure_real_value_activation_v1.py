from pathlib import Path

UI = Path("backend/app/ui/fund_analysis_center.py")


def test_zero_real_value_diagnostic_is_present():
    text = UI.read_text(encoding="utf-8")
    assert "zero_like_symbols = []" in text
    assert "shares_held / market_value" in text
    assert "fund_free_float_ratio" in text


def test_safety_contract_remains_none():
    text = UI.read_text(encoding="utf-8")
    assert "otomatik AL/SAT yetkisi yoktur" in text
