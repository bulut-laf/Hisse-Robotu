from __future__ import annotations

import pandas as pd

from app.analysis.intraday_movement_evidence import (
    build_intraday_movement_evidence,
)


def _frame(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [value + 0.2 for value in closes],
            "Low": [value - 0.2 for value in closes],
            "Close": closes,
            "Volume": [100.0] * len(closes),
        }
    )


def test_positive_continuous_structure():
    result = build_intraday_movement_evidence(
        "ASELS.IS",
        _frame([100, 100, 101, 102, 103, 104, 105]),
    )

    assert result.movement_structure == "POZITIF_SUREKLI"


def test_recovery_structure():
    result = build_intraday_movement_evidence(
        "BIMAS.IS",
        _frame([100, 101, 99, 98, 97, 98, 99]),
    )

    assert result.movement_structure == "TOPARLANIYOR"


def test_weakening_recovery_structure():
    result = build_intraday_movement_evidence(
        "TUPRS.IS",
        _frame([100, 99, 101, 100, 99, 98, 99]),
    )

    assert result.movement_structure == "TOPARLANMA_ZAYIF"


def test_negative_continuous_structure():
    result = build_intraday_movement_evidence(
        "GARAN.IS",
        _frame([105, 104, 103, 102, 101, 100, 99]),
    )

    assert result.movement_structure == "NEGATIF_SUREKLI"


def test_mixed_structure_is_neutral():
    # Son fiyat 101:
    # 5m  = 101 / 102 -> -
    # 15m = 101 / 100 -> +
    # 30m = 101 / 100 -> +
    # Bu kombinasyon mevcut kurala göre NOTR'dir.
    result = build_intraday_movement_evidence(
        "AKBNK.IS",
        _frame([100, 99, 98, 97, 100, 102, 101]),
    )

    assert result.movement_structure == "NOTR"


def test_structure_requires_30m_data():
    result = build_intraday_movement_evidence(
        "THYAO.IS",
        _frame([100, 101, 102]),
    )

    assert result.movement_structure == "YETERSIZ_VERI"
