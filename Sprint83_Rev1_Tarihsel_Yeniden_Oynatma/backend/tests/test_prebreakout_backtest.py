from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from backend.app.prebreakout.prebreakout_backtest import (
    PreBreakoutReplayError,
    replay_ozeti,
    tarihsel_yeniden_oynat,
)


def tarihsel_veri(gun: int = 120) -> pd.DataFrame:
    index = pd.bdate_range("2026-01-02", periods=gun)
    close = np.linspace(100.0, 118.0, gun)
    close += np.sin(np.linspace(0.0, 10.0, gun))
    spread = np.linspace(2.0, 1.0, gun)
    volume = np.full(gun, 2_000_000.0)
    volume[-15:] = 2_300_000.0

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


def test_yeniden_oynatma_kesim_sonrasi_veriyi_analizde_kullanmaz() -> None:
    data = tarihsel_veri()
    cutoff = data.index[89].date()

    result = tarihsel_yeniden_oynat(
        "TEST.IS",
        data,
        cutoff,
    )

    assert result.cutoff_date == cutoff
    assert result.entry_close == pytest.approx(float(data.iloc[89]["Close"]))
    assert result.analysis.features is not None
    assert result.analysis.features.close == pytest.approx(
        float(data.iloc[89]["Close"])
    )


def test_ileri_performans_1_3_5_10_20_gun_uretilir() -> None:
    data = tarihsel_veri()
    cutoff = data.index[89].date()

    result = tarihsel_yeniden_oynat("TEST.IS", data, cutoff)

    assert [item.horizon for item in result.forward] == [1, 3, 5, 10, 20]
    assert all(item.available for item in result.forward)


def test_ileri_performans_yetersizse_mevcut_degil_isaretlenir() -> None:
    data = tarihsel_veri(100)
    cutoff = data.index[94].date()

    result = tarihsel_yeniden_oynat("TEST.IS", data, cutoff)

    twenty_day = next(item for item in result.forward if item.horizon == 20)
    assert twenty_day.available is False
    assert twenty_day.close_return_pct is None


def test_bos_veri_reddedilir() -> None:
    with pytest.raises(PreBreakoutReplayError):
        tarihsel_yeniden_oynat(
            "TEST.IS",
            pd.DataFrame(),
            date(2026, 7, 1),
        )


def test_gecersiz_ufuk_reddedilir() -> None:
    data = tarihsel_veri()
    cutoff = data.index[89].date()

    with pytest.raises(PreBreakoutReplayError):
        tarihsel_yeniden_oynat(
            "TEST.IS",
            data,
            cutoff,
            horizons=(0,),
        )


def test_ozet_bos_listeyi_guvenli_isler() -> None:
    summary = replay_ozeti([])

    assert summary.total_replays == 0
    assert summary.accepted_candidates == 0
    assert summary.positive_5d_rate_pct == 0.0


def test_ozet_sayimlari_tutarlidir() -> None:
    data = tarihsel_veri()
    cutoffs = [
        data.index[80].date(),
        data.index[85].date(),
        data.index[90].date(),
    ]

    results = [
        tarihsel_yeniden_oynat("TEST.IS", data, cutoff)
        for cutoff in cutoffs
    ]
    summary = replay_ozeti(results)

    assert summary.total_replays == 3
    assert (
        summary.accepted_candidates
        + summary.late_entry_count
        + summary.rejected_count
        == 3
    )
