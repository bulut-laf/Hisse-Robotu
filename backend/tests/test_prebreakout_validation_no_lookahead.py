from datetime import date

import numpy as np
import pandas as pd

from backend.app.prebreakout.prebreakout_validation import (
    PreBreakoutValidationConfig,
    toplu_tarihsel_dogrulama,
)


def veri() -> pd.DataFrame:
    index = pd.bdate_range("2026-01-02", periods=140)
    close = np.linspace(100.0, 114.0, 140)
    return pd.DataFrame(
        {
            "Open": close - 0.2,
            "High": close + 0.8,
            "Low": close - 0.8,
            "Close": close,
            "Volume": np.full(140, 2_000_000.0),
        },
        index=index,
    )


def test_gelecek_verisi_degisse_bile_kesim_gunu_analizi_degismez() -> None:
    original = veri()
    changed = original.copy()

    cutoff = pd.Timestamp("2026-05-15")
    future_mask = changed.index > cutoff
    changed.loc[future_mask, ["Open", "High", "Low", "Close"]] *= 2.0

    config = PreBreakoutValidationConfig(
        start_date=cutoff.date(),
        end_date=cutoff.date(),
        cutoff_step=1,
        minimum_score=0,
    )

    first = toplu_tarihsel_dogrulama(
        {"TEST.IS": original},
        config,
    )
    second = toplu_tarihsel_dogrulama(
        {"TEST.IS": changed},
        config,
    )

    assert len(first) == len(second) == 1
    assert first[0].replay.analysis == second[0].replay.analysis
    assert first[0].replay.entry_close == second[0].replay.entry_close
