from datetime import date
from types import SimpleNamespace

import pytest

from backend.app.ui import momentum_batch_history_integration as mod


def test_momentum_batch_scan_day_request_ve_export(monkeypatch):
    captured = {}

    class FakeService:
        def calistir(self, request):
            captured["request"] = request
            return SimpleNamespace()

    monkeypatch.setattr(mod, "MomentumWalkForwardService", lambda: FakeService())
    monkeypatch.setattr(
        mod,
        "walk_forward_tablosu",
        lambda result: (
            {"Hisse": "TRMET", "Sıra": 20},
            {"Hisse": "EFOR", "Sıra": 13},
        ),
    )

    rows = mod.momentum_batch_scan_day(
        date(2026, 7, 1),
        "BIST100",
        minimum_skor=55,
        maksimum_aday=25,
        ozel_semboller=(),
        internetten_guncelle=False,
    )

    request = captured["request"]
    assert request.evren == "BIST 100"
    assert request.kesim_tarihi == "2026-07-01"
    assert request.minimum_skor == 55
    assert request.maksimum_aday == 25
    assert rows[0]["Hisse"] == "TRMET"


def test_render_panel_scan_day_koprusu(monkeypatch):
    captured = {}

    def fake_render(st, *, scan_day, default_start_date, default_end_date, universe_options):
        captured["universes"] = universe_options
        return "OK"

    monkeypatch.setattr(mod, "render_batch_historical_export_panel", fake_render)

    result = mod.render_momentum_batch_history_panel(
        object(),
        minimum_skor=55,
        maksimum_aday=25,
        ozel_semboller=("THYAO.IS",),
        internetten_guncelle=False,
        default_start_date=date(2026, 6, 29),
        default_end_date=date(2026, 7, 29),
    )

    assert result == "OK"
    assert captured["universes"] == ("BIST100", "BIST Tüm")
