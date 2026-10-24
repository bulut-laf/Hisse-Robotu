from __future__ import annotations

import pandas as pd

from app.operations.scheduled_intraday_batch import (
    fetch_scheduled_intraday_batch,
)


def _frame() -> pd.DataFrame:
    index = pd.date_range(
        "2026-10-08 10:00",
        periods=7,
        freq="5min",
        tz="Europe/Istanbul",
    )

    closes = [100, 100, 101, 102, 103, 104, 105]

    return pd.DataFrame(
        {
            ("THYAO.IS", "Open"): closes,
            ("THYAO.IS", "High"): [x + 0.2 for x in closes],
            ("THYAO.IS", "Low"): [x - 0.2 for x in closes],
            ("THYAO.IS", "Close"): closes,
            ("THYAO.IS", "Volume"): [100] * 6 + [150],
        },
        index=index,
    )


def test_scheduled_batch_produces_freshness_with_evidence():
    raw = _frame()

    def downloader(**_: object) -> pd.DataFrame:
        return raw

    result = fetch_scheduled_intraday_batch(
        ("THYAO.IS",),
        now=pd.Timestamp(
            "2026-10-08 10:40",
            tz="Europe/Istanbul",
        ).to_pydatetime(),
        downloader=downloader,
    )

    assert result.successful_count == 1
    assert result.evidence_count == 1
    assert result.freshness_count == 1

    freshness = result.freshness["THYAO.IS"]

    assert freshness.symbol == "THYAO.IS"
    assert freshness.state == "DATA_GUNCEL"
    assert freshness.locked is False
    assert freshness.missing_bar_count == 0

    evidence = result.evidence["THYAO.IS"]

    assert evidence.symbol == "THYAO.IS"
    assert evidence.movement_structure == "POZITIF_SUREKLI"
