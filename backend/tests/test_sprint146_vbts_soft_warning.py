from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

import backend.app.analysis.market_scanner as market_scanner
from backend.app.analysis.market_scanner import (
    BistMarketScannerService,
    MarketScanRequest,
)
from backend.app.compliance.vbts_scan_filter import VbtsDatasetNotUsableError


class _FakeScanner:
    def __init__(self) -> None:
        self.received_symbols = ()

    def tara(self, *, semboller, ilerleme_bildirimi=None):
        self.received_symbols = tuple(semboller)
        rows = tuple(
            SimpleNamespace(
                sembol=symbol,
                kapanis=10.0,
                analiz_tarihi=date(2026, 8, 4),
            )
            for symbol in self.received_symbols
        )
        return SimpleNamespace(basarili_sonuclar=rows)


class _WarningFilter:
    def apply(self, *, symbols, control_date, control_time):
        return SimpleNamespace(
            allowed_symbols=("AAA.IS",),
            blocked_symbols=("BBB.IS",),
            block_reasons={"BBB.IS": ("Brüt takas",)},
        )


class _StaleFilter:
    def apply(self, *, symbols, control_date, control_time):
        raise VbtsDatasetNotUsableError("VBTS veri paketi güncel değil.")

    def apply_known_measures(self, *, symbols, control_date):
        return SimpleNamespace(
            allowed_symbols=("AAA.IS",),
            blocked_symbols=("BBB.IS",),
            block_reasons={"BBB.IS": ("Brüt takas",)},
        )


def _patch_scan_pipeline(monkeypatch):
    monkeypatch.setattr(
        market_scanner,
        "tarama_evreni_yukle",
        lambda *args, **kwargs: (
            ("AAA.IS", "BBB.IS"),
            "test",
            "2026-08-04",
        ),
    )
    monkeypatch.setattr(
        market_scanner,
        "profil_al",
        lambda name: SimpleNamespace(ad="Dengeli", kriterler=object()),
    )

    def _filtered(*, tarama, kriterler):
        return SimpleNamespace(
            adaylar=tuple(tarama.basarili_sonuclar),
            aday_sayisi=len(tarama.basarili_sonuclar),
            elenen_sayisi=0,
            hatali_sayisi=0,
            elenenler=(),
            hatalar=(),
        )

    monkeypatch.setattr(
        market_scanner,
        "tarama_sonucunu_filtrele",
        _filtered,
    )
    monkeypatch.setattr(
        market_scanner,
        "toplu_veri_tazeligini_degerlendir",
        lambda data: None,
    )


def _request() -> MarketScanRequest:
    return MarketScanRequest(
        evren="BIST 100",
        profil_adi="dengeli",
        maksimum_aday=15,
        internetten_evren_guncelle=False,
    )


def test_soft_vbts_mode_keeps_restricted_symbol_in_scan(monkeypatch):
    _patch_scan_pipeline(monkeypatch)
    scanner = _FakeScanner()

    service = BistMarketScannerService(
        evren_repository=object(),
        tarayici=scanner,
        vbts_scan_filter=_WarningFilter(),
        vbts_control_date=date(2026, 8, 4),
        vbts_control_time=datetime(2026, 8, 4, 18, 40, tzinfo=timezone.utc),
        vbts_hard_block=False,
    )

    result = service.calistir(_request())

    assert scanner.received_symbols == ("AAA.IS", "BBB.IS")
    assert result.vbts_engellenen_semboller == ("BBB.IS",)
    assert result.vbts_engelleme_nedenleri == {
        "BBB.IS": ("Brüt takas",)
    }


def test_soft_vbts_mode_continues_when_dataset_is_stale(monkeypatch):
    _patch_scan_pipeline(monkeypatch)
    scanner = _FakeScanner()

    service = BistMarketScannerService(
        evren_repository=object(),
        tarayici=scanner,
        vbts_scan_filter=_StaleFilter(),
        vbts_control_date=date(2026, 8, 4),
        vbts_control_time=datetime(2026, 8, 4, 18, 40, tzinfo=timezone.utc),
        vbts_hard_block=False,
    )

    result = service.calistir(_request())

    assert scanner.received_symbols == ("AAA.IS", "BBB.IS")
    assert result.vbts_engellenen_semboller == ("BBB.IS",)
    assert result.vbts_engelleme_nedenleri == {
        "BBB.IS": ("Brüt takas",)
    }
    assert result.vbts_dogrulama_uyarisi is not None
    assert "yeni tedbirler eksik olabilir" in result.vbts_dogrulama_uyarisi
