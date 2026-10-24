from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from backend.app.prebreakout.prebreakout_candidate_lifecycle import CandidatePriceObservation
from backend.app.prebreakout.prebreakout_live_performance import (
    LivePerformanceLabel,
    canli_performans_ozeti,
    canli_performanslari_kaydet,
    canli_performanslari_yukle,
    canli_sinyal_performansini_hesapla,
)
from backend.app.prebreakout.prebreakout_live_watch import PreBreakoutLiveSignal


def _signal() -> PreBreakoutLiveSignal:
    return PreBreakoutLiveSignal(
        schema_version=1,
        signal_id="test-signal",
        symbol="TUPRS.IS",
        signal_date="2026-01-01",
        recorded_at_utc="2026-01-01T12:00:00Z",
        stage="E3",
        stage_label="E3",
        score=70,
        accepted=True,
        close=100.0,
        minimum_momentum_score=10,
        threshold_policy_enabled=True,
        threshold_policy_source="test",
        features={},
        reasons=(),
        risks=(),
        payload_sha256="hash",
    )


def _observations(closes: list[float], highs: list[float] | None = None, lows: list[float] | None = None):
    base = date(2026, 1, 1)
    highs = highs or [value + 1.0 for value in closes]
    lows = lows or [value - 1.0 for value in closes]
    return tuple(
        CandidatePriceObservation(
            observation_date=base + timedelta(days=index),
            high=high,
            low=low,
            close=close,
        )
        for index, (close, high, low) in enumerate(zip(closes, highs, lows), start=1)
    )


def test_5_10_20_gunluk_sonuclar_hesaplanir() -> None:
    closes = [100.0 + index * 0.5 for index in range(1, 21)]
    highs = [value + 2.0 for value in closes]
    result = canli_sinyal_performansini_hesapla(_signal(), _observations(closes, highs=highs))
    assert [item.horizon for item in result.horizons] == [5, 10, 20]
    assert all(item.close_return_pct is not None for item in result.horizons)
    assert result.horizons[-1].max_return_pct is not None
    assert result.horizons[-1].min_return_pct is not None
    assert result.horizons[-1].max_drawdown_pct is not None


def test_20_gun_tamamlanmadan_olculemiyor() -> None:
    result = canli_sinyal_performansini_hesapla(_signal(), _observations([101.0] * 10))
    assert result.label is LivePerformanceLabel.OLCULEMIYOR
    assert result.horizons[-1].measured_session_count == 10
    assert result.horizons[-1].close_return_pct is None


def test_guclu_20_gunluk_hareket_basarili() -> None:
    closes = [101.0 + index * 0.3 for index in range(20)]
    highs = [value + 5.0 for value in closes]
    result = canli_sinyal_performansini_hesapla(_signal(), _observations(closes, highs=highs))
    assert result.label is LivePerformanceLabel.BASARILI


def test_kisa_yukselip_20_gunde_negatif_kapanan_sinirli() -> None:
    closes = [104.0] * 5 + [102.0] * 5 + [99.0] * 10
    highs = [111.0] * 5 + [104.0] * 15
    lows = [98.0] * 20
    result = canli_sinyal_performansini_hesapla(_signal(), _observations(closes, highs, lows))
    assert result.label is LivePerformanceLabel.SINIRLI_HAREKET


def test_guclu_negatif_sonuc_basarisiz() -> None:
    closes = [99.0 - index * 0.4 for index in range(20)]
    lows = [value - 4.0 for value in closes]
    result = canli_sinyal_performansini_hesapla(_signal(), _observations(closes, lows=lows))
    assert result.label is LivePerformanceLabel.BASARISIZ


def test_sinyal_gunu_ve_onceki_veriler_kullanilmaz() -> None:
    signal = _signal()
    observations = (
        CandidatePriceObservation(date(2025, 12, 31), 200.0, 50.0, 150.0),
        CandidatePriceObservation(date(2026, 1, 1), 200.0, 50.0, 150.0),
        *_observations([101.0] * 5),
    )
    result = canli_sinyal_performansini_hesapla(signal, observations)
    assert result.available_session_count == 5
    assert result.horizons[0].close_return_pct == 1.0


def test_ozet_ve_kayit_yukleme(tmp_path: Path) -> None:
    measured = canli_sinyal_performansini_hesapla(_signal(), _observations([101.0 + i * 0.3 for i in range(20)], highs=[112.0] * 20))
    pending = canli_sinyal_performansini_hesapla(_signal(), _observations([101.0] * 5))
    summary = canli_performans_ozeti((measured, pending))
    assert summary["TOPLAM"] == 2
    assert summary["ÖLÇÜLEN"] == 1
    path = tmp_path / "performance.json"
    canli_performanslari_kaydet((measured, pending), path)
    loaded = canli_performanslari_yukle(path)
    assert loaded == (measured, pending)
