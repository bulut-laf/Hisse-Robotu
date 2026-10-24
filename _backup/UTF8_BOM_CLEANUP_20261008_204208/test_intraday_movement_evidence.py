from __future__ import annotations

import pandas as pd

from app.analysis.intraday_movement_evidence import (
    build_intraday_movement_evidence,
)


def _frame(
    closes: list[float],
    volumes: list[float],
) -> pd.DataFrame:
    assert len(closes) == len(volumes)

    return pd.DataFrame(
        {
            "Open": closes,
            "High": [value + 0.20 for value in closes],
            "Low": [value - 0.20 for value in closes],
            "Close": closes,
            "Volume": volumes,
        }
    )


def test_intraday_evidence_calculates_short_term_movement():
    frame = _frame(
        [100, 100, 100, 101, 102, 103, 104],
        [100, 100, 100, 100, 100, 100, 150],
    )

    result = build_intraday_movement_evidence("THYAO.IS", frame)

    assert result.symbol == "THYAO.IS"
    assert result.bar_count == 7
    assert result.last_price == 104.0
    assert result.price_change_5m_pct > 0
    assert result.price_change_15m_pct > 0
    assert result.price_change_30m_pct > 0
    assert result.movement_state == "POZITIF"
    assert result.volume_state == "DESTEKLIYOR"
    assert result.data_sufficient is True


def test_intraday_evidence_detects_negative_movement():
    frame = _frame(
        [104, 104, 103, 102, 101, 100, 99],
        [100, 100, 100, 100, 100, 100, 60],
    )

    result = build_intraday_movement_evidence("AKBNK.IS", frame)

    assert result.movement_state == "NEGATIF"
    assert result.volume_state == "ZAYIF"


def test_intraday_evidence_detects_rebound_from_day_low():
    frame = _frame(
        [100, 98, 96, 95, 96, 97, 98],
        [100, 100, 100, 100, 100, 100, 100],
    )

    result = build_intraday_movement_evidence("ASELS.IS", frame)

    assert result.rebound_from_day_low_pct is not None
    assert result.rebound_state == "VAR"


def test_intraday_evidence_requires_enough_bars():
    frame = _frame(
        [100, 101, 102],
        [100, 100, 100],
    )

    result = build_intraday_movement_evidence("BIMAS.IS", frame)

    assert result.data_sufficient is False
    assert result.price_change_5m_pct is not None
    assert result.price_change_15m_pct is None
    assert result.price_change_30m_pct is None
    assert result.volume_ratio_5m is None


def test_intraday_evidence_handles_empty_frame():
    result = build_intraday_movement_evidence(
        "TUPRS.IS",
        pd.DataFrame(),
    )

    assert result.data_sufficient is False
    assert result.movement_state == "YETERSIZ_VERI"
    assert result.error is not None


def test_intraday_evidence_handles_missing_columns():
    frame = pd.DataFrame(
        {
            "Close": [100, 101],
            "Volume": [100, 100],
        }
    )

    result = build_intraday_movement_evidence("EREGL.IS", frame)

    assert result.data_sufficient is False
    assert result.movement_state == "YETERSIZ_VERI"
    assert "eksik kolon" in result.error
