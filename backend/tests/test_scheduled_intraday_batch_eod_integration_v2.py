import pandas as pd

from app.analysis.eod_decision_gate import EodDecisionState
from app.operations.scheduled_intraday_batch import run_scheduled_intraday_batch


def _frame():
    return pd.DataFrame(
        {
            "Open":   [100, 100, 101, 102, 103, 104, 105],
            "High":   [101, 101, 102, 103, 104, 105, 106],
            "Low":    [99, 99, 100, 101, 102, 103, 104],
            "Close":  [100, 100, 101, 102, 103, 104, 105],
            "Volume": [100, 100, 100, 100, 100, 100, 150],
        }
    )


def test_batch_produces_eod_decision_from_existing_analysis():
    monkeypatch_frame = _frame()

    # Batch'in mevcut indirme katmanını bypass ediyoruz.
    # Aynı 5m frame movement/freshness/validation/close katmanlarına gidecek.
    from unittest.mock import patch

    with patch(
        "app.operations.scheduled_intraday_batch._download_5m_batch",
        return_value={"THYAO.IS": monkeypatch_frame},
    ):
        result = run_scheduled_intraday_batch(
            ["THYAO.IS"],
            now=pd.Timestamp("2026-10-08 10:55", tz="Europe/Istanbul").to_pydatetime(),
        )

    assert "THYAO.IS" in result.eod_decisions

    decision = result.eod_decisions["THYAO.IS"]

    assert decision.state in {
        EodDecisionState.ALIS_ADAYI,
        EodDecisionState.BEKLE,
        EodDecisionState.ELENDI,
    }


def test_batch_eod_decision_is_not_created_without_validation():
    from unittest.mock import patch

    with patch(
        "app.operations.scheduled_intraday_batch._download_5m_batch",
        return_value={},
    ):
        result = run_scheduled_intraday_batch(
            ["THYAO.IS"],
            now=pd.Timestamp("2026-10-08 10:55", tz="Europe/Istanbul").to_pydatetime(),
        )

    assert result.eod_decisions == {}
