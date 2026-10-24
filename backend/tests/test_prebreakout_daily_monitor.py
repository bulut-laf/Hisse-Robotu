from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import pytest

from backend.app.prebreakout.prebreakout_candidate_lifecycle import CandidatePriceObservation
from backend.app.prebreakout.prebreakout_live_watch import PreBreakoutLiveSignal
from backend.app.prebreakout.prebreakout_paper_portfolio import PaperTradeStatus
from backend.app.prebreakout.prebreakout_threshold_policy import PreBreakoutThresholdPolicy
import backend.app.prebreakout.prebreakout_daily_monitor as daily


def _signal(symbol: str = "TUPRS.IS") -> PreBreakoutLiveSignal:
    return PreBreakoutLiveSignal(
        schema_version=1,
        signal_id=f"signal-{symbol}",
        symbol=symbol,
        signal_date="2026-01-01",
        recorded_at_utc="2026-01-01T18:00:00Z",
        stage="E3",
        stage_label="E3",
        score=80,
        accepted=True,
        close=100.0,
        minimum_momentum_score=10,
        threshold_policy_enabled=False,
        threshold_policy_source="default",
        features={},
        reasons=(),
        risks=(),
        payload_sha256="x",
    )


def _observations(count: int = 20):
    return tuple(
        CandidatePriceObservation(
            date(2026, 1, 2 + i),
            102.0 + i * 0.6,
            99.0 + i * 0.2,
            101.0 + i * 0.5,
        )
        for i in range(count)
    )


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signals):
    monkeypatch.setattr(daily, "canli_sinyalleri_kaydet", lambda *a, **k: tuple(signals))
    monkeypatch.setattr(daily, "canli_sinyalleri_yukle", lambda *a, **k: tuple(signals))
    return daily.gunluk_izleme_akisini_calistir(
        [],
        date(2026, 2, 1),
        PreBreakoutThresholdPolicy(),
        {signals[0].symbol: _observations()} if signals else {},
        live_watch_path=tmp_path / "live.jsonl",
        lifecycle_path=tmp_path / "life.json",
        performance_path=tmp_path / "perf.json",
        paper_trades_path=tmp_path / "paper.json",
        daily_report_path=tmp_path / "daily.json",
    )


def test_gunluk_akis_butun_zinciri_calistirir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run(tmp_path, monkeypatch, [_signal()])
    assert result.new_signal_count == 1
    assert result.total_signal_count == 1
    assert len(result.lifecycle_records) == 1
    assert len(result.performance_records) == 1
    assert len(result.paper_trades) == 1


def test_gunluk_akis_dosyalari_uretir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _run(tmp_path, monkeypatch, [_signal()])
    for name in ("life.json", "perf.json", "paper.json", "daily.json"):
        assert (tmp_path / name).exists()


def test_gunluk_ozet_json_gecerlidir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _run(tmp_path, monkeypatch, [_signal()])
    payload = json.loads((tmp_path / "daily.json").read_text(encoding="utf-8"))
    assert payload["run_date"] == "2026-02-01"
    assert payload["total_signal_count"] == 1
    assert payload["paper_trade_count"] == 1


def test_eksik_fiyat_verisi_akisi_durdurmaz(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    signal = _signal("THYAO.IS")
    monkeypatch.setattr(daily, "canli_sinyalleri_kaydet", lambda *a, **k: (signal,))
    monkeypatch.setattr(daily, "canli_sinyalleri_yukle", lambda *a, **k: (signal,))
    result = daily.gunluk_izleme_akisini_calistir(
        [], date(2026, 2, 1), PreBreakoutThresholdPolicy(), {},
        live_watch_path=tmp_path / "live.jsonl",
        lifecycle_path=tmp_path / "life.json",
        performance_path=tmp_path / "perf.json",
        paper_trades_path=tmp_path / "paper.json",
        daily_report_path=tmp_path / "daily.json",
    )
    assert result.missing_observation_symbols == ("THYAO.IS",)
    assert result.performance_records[0].available_session_count == 0
    assert result.paper_trades[0].status is PaperTradeStatus.ACIK


def test_sembol_eslestirmesi_buyuk_kucuk_harfe_duyarsizdir() -> None:
    rows = _observations(2)
    assert daily._observations_for("tuprs.is", {"TUPRS.IS": rows}) == rows


def test_portfoy_ozeti_gunluk_sonuca_dahil_edilir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run(tmp_path, monkeypatch, [_signal()])
    assert result.portfolio_summary.total_trade_count == 1


def test_bos_sinyal_listesi_guvenle_islenir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run(tmp_path, monkeypatch, [])
    assert result.total_signal_count == 0
    assert result.portfolio_summary.total_trade_count == 0


def test_gunluk_akis_canli_kayitta_cooldown_ayarini_aktarir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}
    monkeypatch.setattr(daily, "canli_sinyalleri_kaydet", lambda *a, **k: captured.update(k) or ())
    monkeypatch.setattr(daily, "canli_sinyalleri_yukle", lambda *a, **k: ())
    daily.gunluk_izleme_akisini_calistir(
        [], date(2026, 2, 1), PreBreakoutThresholdPolicy(), {},
        live_watch_path=tmp_path / "live.jsonl",
        lifecycle_path=tmp_path / "life.json",
        performance_path=tmp_path / "perf.json",
        paper_trades_path=tmp_path / "paper.json",
        daily_report_path=tmp_path / "daily.json",
    )
    assert captured["duplicate_cooldown_days"] == 5
