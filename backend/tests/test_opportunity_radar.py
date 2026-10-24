from __future__ import annotations

import numpy as np
import pandas as pd

from backend.app.opportunity_radar import _weekly_enrich, _weekly


def _daily_frame(days: int = 420) -> pd.DataFrame:
    idx = pd.bdate_range("2025-01-01", periods=days)
    base = pd.Series(np.linspace(100.0, 145.0, days), index=idx)
    return pd.DataFrame(
        {
            "Open": base * 0.995,
            "High": base * 1.02,
            "Low": base * 0.98,
            "Close": base,
            "Volume": np.linspace(1_000_000, 1_500_000, days),
        },
        index=idx,
    )


def test_weekly_contract_produces_expected_columns():
    out = _weekly_enrich(_weekly(_daily_frame()))
    assert {"WeeklyScore", "Stage", "DistResPct", "RSI14", "VolRatio", "ATRPct"}.issubset(out.columns)
    assert out["WeeklyScore"].dropna().between(0, 100).all()
