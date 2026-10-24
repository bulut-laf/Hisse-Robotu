from pathlib import Path


def test_opportunity_radar_dashboard_wiring():
    dashboard = Path(__file__).resolve().parents[1] / "dashboard.py"
    text = dashboard.read_text(encoding="utf-8")
    assert '"Fırsat Radarı"' in text
    assert "render_opportunity_radar" in text
