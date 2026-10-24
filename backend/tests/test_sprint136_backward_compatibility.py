from datetime import date
from types import SimpleNamespace

from backend.app.ui import momentum_batch_history_integration as mod


def test_sprint135_api_korunuyor():
    assert hasattr(mod, "momentum_batch_scan_day")
    assert hasattr(mod, "render_momentum_batch_history_panel")
    assert hasattr(mod, "render_batch_historical_export_panel")
    assert hasattr(mod, "ReusableMomentumBatchScanner")


def test_eski_render_panel_sozlesmesi_calismaya_devam_eder(monkeypatch):
    captured = {}

    def fake_render(st, *, scan_day, default_start_date, default_end_date, universe_options):
        captured["universes"] = universe_options
        return "OK"

    monkeypatch.setattr(mod, "render_batch_historical_export_panel", fake_render)

    result = mod.render_momentum_batch_history_panel(
        object(),
        minimum_skor=55,
        maksimum_aday=25,
        ozel_semboller=(),
        internetten_guncelle=False,
        default_start_date=date(2026, 6, 29),
        default_end_date=date(2026, 7, 29),
    )

    assert result == "OK"
    assert captured["universes"] == ("BIST100", "BIST Tüm")
