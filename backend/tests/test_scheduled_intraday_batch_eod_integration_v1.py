from types import SimpleNamespace

from app.analysis.eod_decision_gate import EodDecisionState
from app.operations.scheduled_intraday_batch import ScheduledIntradayBatchResult


def test_batch_result_can_store_final_eod_decision():
    decision = SimpleNamespace(
        state=EodDecisionState.ALIS_ADAYI,
        reason="Intraday hareket destekliyor, kapanış pozitif.",
    )

    result = ScheduledIntradayBatchResult(
        snapshots={},
        evidence={},
        freshness={},
        validation={},
        failures=(),
        requested_count=1,
        eod_decisions={"THYAO.IS": decision},
    )

    assert result.eod_decisions["THYAO.IS"].state == EodDecisionState.ALIS_ADAYI
    assert result.eod_decision_count == 1


def test_batch_result_keeps_decision_per_symbol():
    decisions = {
        "THYAO.IS": SimpleNamespace(state=EodDecisionState.ALIS_ADAYI),
        "AKBNK.IS": SimpleNamespace(state=EodDecisionState.BEKLE),
        "GARAN.IS": SimpleNamespace(state=EodDecisionState.ELENDI),
    }

    result = ScheduledIntradayBatchResult(
        snapshots={},
        evidence={},
        freshness={},
        validation={},
        failures=(),
        requested_count=3,
        eod_decisions=decisions,
    )

    assert result.eod_decision_count == 3
    assert result.eod_decisions["THYAO.IS"].state == EodDecisionState.ALIS_ADAYI
    assert result.eod_decisions["AKBNK.IS"].state == EodDecisionState.BEKLE
    assert result.eod_decisions["GARAN.IS"].state == EodDecisionState.ELENDI
