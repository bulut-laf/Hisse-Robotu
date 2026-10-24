from __future__ import annotations

import numpy as np
import pandas as pd


def ornek_veri(
    gun: int = 90,
    *,
    son_gun_sicrama_pct: float = 0.0,
    hacim_carpani: float = 1.15,
) -> pd.DataFrame:
    index = pd.date_range("2026-03-01", periods=gun, freq="D")
    base = np.linspace(100.0, 106.0, gun)
    wave = np.sin(np.linspace(0.0, 8.0, gun)) * 1.2
    close = base + wave
    close[-10:] = np.linspace(close[-10], 107.0, 10)
    if son_gun_sicrama_pct:
        close[-1] = close[-2] * (1.0 + son_gun_sicrama_pct / 100.0)

    spread = np.linspace(2.6, 1.0, gun)
    volume = np.full(gun, 2_000_000.0)
    volume[-3:] *= hacim_carpani

    return pd.DataFrame(
        {
            "Open": close - 0.20,
            "High": close + spread / 2,
            "Low": close - spread / 2,
            "Close": close,
            "Volume": volume,
        },
        index=index,
    )
