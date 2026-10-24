from pathlib import Path


def test_ui_has_index_content_headings() -> None:
    text = Path("backend/app/ui/bist_daily_market_dashboard.py").read_text(encoding="utf-8")
    assert '"BIST Tüm": "BIST Tüm"' in text
    assert '"XU100": "BIST 100"' in text
    assert '"XU50": "BIST 50"' in text
    assert '"XU30": "BIST 30"' in text
    assert '"Özel Liste": None' in text
    assert '"Piyasa içeriği"' in text
    assert "selected_display" in text