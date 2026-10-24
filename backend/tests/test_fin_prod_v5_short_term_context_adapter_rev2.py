
from pathlib import Path
from backend.app.analysis.fin_prod_v5_short_term_context_adapter import _market_symbol

def test_market_symbol_is_bist_yahoo_style():
    value = _market_symbol("TUPRS")
    assert value.upper().endswith(".IS")

def test_rev2_broadens_existing_symbol_json_evidence_without_scoring():
    from backend.app.analysis import fin_prod_v5_short_term_context_adapter as m
    text = Path(m.__file__).read_text(encoding="utf-8")
    assert "_discover_symbol_jsons" in text
    assert "No metric is guessed." in text
    assert "Missing metrics remain null." in text
    assert "skoru_hesapla" not in text
    assert "calculate_short_term_investability(" not in text
