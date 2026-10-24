from datetime import date

import numpy as np
import pandas as pd

from backend.app.prebreakout.prebreakout_backtest import (
    replay_ozeti,
    tarihsel_yeniden_oynat,
)
from backend.app.prebreakout.prebreakout_report import (
    replay_ozetini_tabloya_cevir,
    replay_sonuclarini_tabloya_cevir,
)


def veri() -> pd.DataFrame:
    index = pd.bdate_range("2026-01-02", periods=120)
    close = np.linspace(100.0, 116.0, 120)
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


def test_replay_sonuclari_dataframe_olur() -> None:
    data = veri()
    result = tarihsel_yeniden_oynat(
        "TEST.IS",
        data,
        data.index[89].date(),
    )

    table = replay_sonuclarini_tabloya_cevir([result])

    assert len(table) == 1
    assert table.loc[0, "symbol"] == "TEST.IS"
    assert "max_return_20d_pct" in table.columns


def test_replay_ozeti_dataframe_olur() -> None:
    data = veri()
    result = tarihsel_yeniden_oynat(
        "TEST.IS",
        data,
        data.index[89].date(),
    )
    summary = replay_ozeti([result])

    table = replay_ozetini_tabloya_cevir(summary)

    assert len(table) == 1
    assert table.loc[0, "total_replays"] == 1
