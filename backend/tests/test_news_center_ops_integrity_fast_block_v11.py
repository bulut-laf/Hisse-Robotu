from pathlib import Path

UI = Path("backend/app/ui/news_center_dashboard.py")


def source() -> str:
    return UI.read_text(encoding="utf-8-sig")


def test_news_center_ops_integrity_fast_block_v11_preserves_existing_terms():
    text = source()
    assert "KAP" in text
    assert "render_official_source_operations_panel(" in text
