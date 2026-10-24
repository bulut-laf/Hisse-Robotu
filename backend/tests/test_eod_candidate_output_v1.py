from types import SimpleNamespace

from app.analysis.eod_decision_gate import EodDecisionState
from app.analysis.eod_candidate_output import build_eod_candidate_output


def _decision(state, reason="test"):
    return SimpleNamespace(
        state=state,
        reason=reason,
    )


def test_only_buy_candidates_are_returned():
    decisions = {
        "THYAO.IS": _decision(EodDecisionState.ALIS_ADAYI),
        "AKBNK.IS": _decision(EodDecisionState.BEKLE),
        "BIMAS.IS": _decision(EodDecisionState.ALIS_ADAYI),
        "GARAN.IS": _decision(EodDecisionState.ELENDI),
    }

    result = build_eod_candidate_output(
        ["THYAO.IS", "AKBNK.IS", "BIMAS.IS", "GARAN.IS"],
        decisions,
    )

    assert result.symbols == ("THYAO.IS", "BIMAS.IS")
    assert result.count == 2


def test_original_candidate_order_is_preserved():
    decisions = {
        "GARAN.IS": _decision(EodDecisionState.ALIS_ADAYI),
        "THYAO.IS": _decision(EodDecisionState.ALIS_ADAYI),
        "BIMAS.IS": _decision(EodDecisionState.ALIS_ADAYI),
    }

    result = build_eod_candidate_output(
        ["BIMAS.IS", "GARAN.IS", "THYAO.IS"],
        decisions,
    )

    assert result.symbols == (
        "BIMAS.IS",
        "GARAN.IS",
        "THYAO.IS",
    )


def test_empty_buy_candidate_list():
    decisions = {
        "THYAO.IS": _decision(EodDecisionState.BEKLE),
        "AKBNK.IS": _decision(EodDecisionState.ELENDI),
    }

    result = build_eod_candidate_output(
        ["THYAO.IS", "AKBNK.IS"],
        decisions,
    )

    assert result.symbols == ()
    assert result.count == 0


def test_missing_decision_is_not_buy_candidate():
    decisions = {
        "THYAO.IS": _decision(EodDecisionState.ALIS_ADAYI),
    }

    result = build_eod_candidate_output(
        ["THYAO.IS", "BIMAS.IS"],
        decisions,
    )

    assert result.symbols == ("THYAO.IS",)
    assert result.count == 1
