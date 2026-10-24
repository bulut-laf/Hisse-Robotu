from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd
import pytest


def _ohlcv(rows: int, start: str = "2024-01-01") -> pd.DataFrame:
    idx = pd.date_range(start, periods=rows, freq="7D")
    close = np.linspace(100.0, 150.0, rows)
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.linspace(1_000_000, 2_000_000, rows),
        },
        index=idx,
    )


@dataclass(frozen=True)
class _Snapshot:
    ad: str
    veri: pd.DataFrame


@dataclass(frozen=True)
class _Package:
    daily: _Snapshot

    def getir(self, name: str):
        if name != "Günlük":
            raise KeyError(name)
        return self.daily


def test_live_bridge_official_bar_updates_daily(monkeypatch):
    from backend.app.data import live_official_data_bridge as bridge

    historical = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [102.0],
            "Low": [99.0],
            "Close": [101.0],
            "Volume": [1000],
        },
        index=pd.to_datetime(["2026-07-30"]),
    )
    official = pd.DataFrame(
        {
            "Open": [110.0],
            "High": [112.0],
            "Low": [109.0],
            "Close": [111.0],
            "Volume": [2000],
        },
        index=pd.to_datetime(["2026-08-03"]),
    )

    class _Result:
        veriler = {"TKFEN.IS": official}

    monkeypatch.setattr(
        bridge,
        "load_latest_official_daily",
        lambda _symbols: _Result(),
    )

    package = _Package(_Snapshot("Günlük", historical))
    updated = bridge.resmi_gunluk_paketi_guncelle(package, "TKFEN")

    daily = updated.getir("Günlük").veri
    assert daily.index[-1].date().isoformat() == "2026-08-03"
    assert float(daily.iloc[-1]["Close"]) == 111.0


def test_weekly_confirmation_does_not_require_sma200_when_history_is_short():
    from types import SimpleNamespace
    from backend.app.analysis.technical_confirmation import (
        zaman_dilimi_teyidini_hesapla,
    )

    snapshot = SimpleNamespace(
        ad="Haftalık",
        interval="1wk",
        veri=_ohlcv(120),
    )

    result = zaman_dilimi_teyidini_hesapla(snapshot)

    assert math.isnan(result.ortalamalar.sma200)
    assert "Yetersiz" in result.ortalamalar.uzun_vade_durumu


def test_daily_confirmation_remains_strict_about_sma200():
    from types import SimpleNamespace
    from backend.app.analysis.technical_confirmation import (
        TechnicalConfirmationError,
        zaman_dilimi_teyidini_hesapla,
    )

    snapshot = SimpleNamespace(
        ad="Günlük",
        interval="1d",
        veri=_ohlcv(120),
    )

    with pytest.raises(TechnicalConfirmationError, match="SMA200"):
        zaman_dilimi_teyidini_hesapla(snapshot)
