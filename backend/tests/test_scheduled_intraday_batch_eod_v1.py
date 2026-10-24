from datetime import datetime
from types import SimpleNamespace

from app.analysis.eod_decision_gate import EodDecisionState


def test_batch_result_has_eod_decisions_container():
    """
    V6 kontratı:
    ScheduledIntradayBatchResult üzerinde eod_decisions bulunmalı.
    """
    from app.operations.scheduled_intraday_batch import ScheduledIntradayBatchResult

    result = ScheduledIntradayBatchResult(
        snapshots={},
        evidence={},
        freshness={},
        validation={},
        failures={},
        requested_count=0,
    )

    assert hasattr(result, "eod_decisions")
    assert result.eod_decisions == {}
    assert result.eod_decision_count == 0


def test_batch_eod_decision_count_tracks_decisions():
    from app.operations.scheduled_intraday_batch import ScheduledIntradayBatchResult

    decision = SimpleNamespace(state=EodDecisionState.ALIS_ADAYI)

    result = ScheduledIntradayBatchResult(
        snapshots={},
        evidence={},
        freshness={},
        validation={},
        failures={},
        requested_count=1,
        eod_decisions={"THYAO.IS": decision},
    )

    assert result.eod_decision_count == 1
    assert result.eod_decisions["THYAO.IS"].state == EodDecisionState.ALIS_ADAYI
