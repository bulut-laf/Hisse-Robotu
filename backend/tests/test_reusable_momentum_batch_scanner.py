from datetime import date
from types import SimpleNamespace

from backend.app.ui import momentum_batch_history_integration as mod


def test_tek_service_ornegi_birden_fazla_gunde_kullanilir(monkeypatch):
    instances = []

    class FakeService:
        def __init__(self):
            instances.append(self)
            self.calls = 0
        def calistir(self, request):
            self.calls += 1
            return SimpleNamespace()

    monkeypatch.setattr(mod, "MomentumWalkForwardService", FakeService)
    monkeypatch.setattr(
        mod,
        "walk_forward_tablosu",
        lambda result: ({"Hisse": "AAA"},),
    )

    scanner = mod.ReusableMomentumBatchScanner(
        minimum_skor=55,
        maksimum_aday=25,
        ozel_semboller=(),
        internetten_guncelle=False,
    )

    scanner.scan_day(date(2026, 7, 1), "BIST100")
    scanner.scan_day(date(2026, 7, 2), "BIST100")

    assert len(instances) == 1
    assert instances[0].calls == 2


def test_request_tarihleri_degiser_ama_service_ayni(monkeypatch):
    seen = []

    class FakeService:
        def calistir(self, request):
            seen.append(request.kesim_tarihi)
            return object()

    monkeypatch.setattr(mod, "MomentumWalkForwardService", FakeService)
    monkeypatch.setattr(mod, "walk_forward_tablosu", lambda result: ())

    scanner = mod.ReusableMomentumBatchScanner(
        minimum_skor=55,
        maksimum_aday=25,
        ozel_semboller=(),
        internetten_guncelle=False,
    )
    scanner.scan_day(date(2026, 7, 1), "BIST100")
    scanner.scan_day(date(2026, 7, 2), "BIST100")

    assert seen == ["2026-07-01", "2026-07-02"]
