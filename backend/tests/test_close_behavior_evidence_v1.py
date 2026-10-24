import pandas as pd

from app.analysis.close_behavior_evidence import (
    CloseBehaviorState,
    build_close_behavior_evidence,
)


def _frame(closes, volumes=None):
    if volumes is None:
        volumes = [100] * len(closes)

    return pd.DataFrame(
        {
            "Open": closes,
            "High": [x + 0.5 for x in closes],
            "Low": [x - 0.5 for x in closes],
            "Close": closes,
            "Volume": volumes,
        }
    )


def test_positive_close():
    result = build_close_behavior_evidence(
        _frame([100, 100.1, 100.2, 100.3, 100.4])
    )

    assert result.close_state == CloseBehaviorState.POZITIF_KAPANIS


def test_weak_close():
    result = build_close_behavior_evidence(
        _frame([100, 100.3, 100.4, 100.2, 100.1])
    )

    assert result.close_state == CloseBehaviorState.ZAYIF_KAPANIS


def test_negative_close():
    result = build_close_behavior_evidence(
        _frame([100, 100.1, 99.9, 99.7, 99.5])
    )

    assert result.close_state == CloseBehaviorState.NEGATIF_KAPANIS


def test_insufficient_data():
    result = build_close_behavior_evidence(
        _frame([100, 100.1])
    )

    assert result.close_state == CloseBehaviorState.YETERSIZ_VERI
