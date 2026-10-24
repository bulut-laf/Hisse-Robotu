from pathlib import Path

def test_ui_handles_date_mismatch():
    source = Path("backend/app/ui/market_context_dashboard.py").read_text(encoding="utf-8")
    assert "MarketContextDateMismatchError" in source
    assert "detected_date" in source

def test_ui_separates_market_and_stock_risks():
    source = Path("backend/app/ui/market_context_dashboard.py").read_text(encoding="utf-8")
    assert "Piyasa / makro riskleri" in source
    assert "Hisse bazlı riskler" in source
    assert "stock_specific_risks" in source

def test_ui_normalizes_manifest_source_names():
    source = Path("backend/app/ui/market_context_dashboard.py").read_text(encoding="utf-8")
    assert "normalize_source_name" in source
