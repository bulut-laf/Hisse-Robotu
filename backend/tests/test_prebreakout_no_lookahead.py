from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.app.prebreakout.prebreakout_backtest import (
    tarihsel_yeniden_oynat,
)


def veri() -> pd.DataFrame:
    index = pd.bdate_range("2026-01-02", periods=120)
    close = np.linspace(100.0, 110.0, 120)
    return pd.DataFrame(
        {
            "Open": close - 0.2,
            "High": close + 0.8,
            "Low": close - 0.8,
            "Close": close,
            "Volume": np.full(120, 2_000_000.0),
        },
        index=index,
    )


def test_kesim_sonrasi_fiyat_degistirilince_analiz_degismez() -> None:
    original = veri()
    cutoff_index = 89
    cutoff = original.index[cutoff_index].date()

    changed = original.copy()
    changed.iloc[cutoff_index + 1 :, changed.columns.get_loc("Close")] *= 5.0
    changed.iloc[cutoff_index + 1 :, changed.columns.get_loc("High")] *= 5.0
    changed.iloc[cutoff_index + 1 :, changed.columns.get_loc("Low")] *= 5.0
    changed.iloc[cutoff_index + 1 :, changed.columns.get_loc("Open")] *= 5.0

    first = tarihsel_yeniden_oynat("TEST.IS", original, cutoff)
    second = tarihsel_yeniden_oynat("TEST.IS", changed, cutoff)

    assert first.analysis == second.analysis
    assert first.entry_close == pytest.approx(second.entry_close)


def test_kesim_sonrasi_fiyat_performans_olcumunu_degistirir() -> None:
    original = veri()
    cutoff_index = 89
    cutoff = original.index[cutoff_index].date()

    changed = original.copy()
    changed.iloc[cutoff_index + 1 :, changed.columns.get_loc("Close")] *= 1.10
    changed.iloc[cutoff_index + 1 :, changed.columns.get_loc("High")] *= 1.10

    first = tarihsel_yeniden_oynat("TEST.IS", original, cutoff)
    second = tarihsel_yeniden_oynat("TEST.IS", changed, cutoff)

    first_5d = next(item for item in first.forward if item.horizon == 5)
    second_5d = next(item for item in second.forward if item.horizon == 5)

    assert first_5d.close_return_pct != second_5d.close_return_pct
