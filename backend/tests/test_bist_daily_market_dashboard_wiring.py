from pathlib import Path


def test_dashboard_bist_gunluk_piyasa_wiring() -> None:
    text = Path("backend/dashboard.py").read_text(encoding="utf-8")
    assert "from backend.app.ui.bist_daily_market_dashboard import render_bist_daily_market" in text
    assert '"BIST Günlük Piyasa",' in text
    assert 'elif analiz_modu == "BIST Günlük Piyasa":' in text
    assert "render_bist_daily_market()" in text
