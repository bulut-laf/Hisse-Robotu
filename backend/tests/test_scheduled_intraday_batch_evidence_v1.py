from __future__ import annotations

import pandas as pd

from app.operations.scheduled_intraday_batch import (
    fetch_scheduled_intraday_batch,
)


def _multi_symbol_frame() -> pd.DataFrame:
    index = pd.date_range(
        "2026-10-08 10:00",
        periods=7,
        freq="5min",
        tz="Europe/Istanbul",
    )

    data: dict[tuple[str, str], list[float]] = {}

    for symbol, base in (
        ("THYAO.IS", 100.0),
        ("AKBNK.IS", 200.0),
    ):
        closes = [
            base,
            base,
            base + 0.5,
            base + 1.0,
            base + 1.5,
            base + 2.0,
            base + 2.5,
        ]

        data[(symbol, "Open")] = closes
        data[(symbol, "High")] = [value + 0.2 for value in closes]
        data[(symbol, "Low")] = [value - 0.2 for value in closes]
        data[(symbol, "Close")] = closes
        data[(symbol, "Volume")] = [
            100,
            100,
            100,
            100,
            100,
            100,
            150,
        ]

    return pd.DataFrame(
        data,
        index=index,
    )


def test_scheduled_batch_produces_evidence_from_same_frame():
    raw = _multi_symbol_frame()

    def downloader(**_: object) -> pd.DataFrame:
        return raw

    result = fetch_scheduled_intraday_batch(
        ("THYAO.IS", "AKBNK.IS"),
        now=pd.Timestamp(
            "2026-10-08 12:00",
            tz="Europe/Istanbul",
        ).to_pydatetime(),
        downloader=downloader,
    )

    assert result.successful_count == 2
    assert result.evidence_count == 2

    assert set(result.evidence) == {
        "THYAO.IS",
        "AKBNK.IS",
    }

    thyao = result.evidence["THYAO.IS"]

    assert thyao.symbol == "THYAO.IS"
    assert thyao.bar_count == 7
    assert thyao.last_price == 102.5
    assert thyao.movement_state == "POZITIF"
    assert thyao.volume_state == "DESTEKLIYOR"

    assert result.failures == ()
