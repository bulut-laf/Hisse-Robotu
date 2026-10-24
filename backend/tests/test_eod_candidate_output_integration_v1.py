from app.analysis.eod_candidate_output import build_eod_candidate_output
from app.analysis.eod_decision_gate import EodDecision, EodDecisionState


def test_v7_preserves_existing_candidate_order():
    candidates = ("THYAO.IS", "BIMAS.IS", "KCHOL.IS", "ASELS.IS")

    decisions = {
        "THYAO.IS": EodDecision(EodDecisionState.ALIS_ADAYI, "uygun"),
        "BIMAS.IS": EodDecision(EodDecisionState.BEKLE, "bekle"),
        "KCHOL.IS": EodDecision(EodDecisionState.ALIS_ADAYI, "uygun"),
        "ASELS.IS": EodDecision(EodDecisionState.ELENDI, "elendi"),
    }

    result = build_eod_candidate_output(candidates, decisions)

    assert result.symbols == ("THYAO.IS", "KCHOL.IS")
    assert result.count == 2


def test_v7_does_not_create_new_candidates():
    candidates = ("THYAO.IS", "BIMAS.IS")

    decisions = {
        "THYAO.IS": EodDecision(EodDecisionState.ALIS_ADAYI, "uygun"),
        "AKBNK.IS": EodDecision(EodDecisionState.ALIS_ADAYI, "uygun"),
    }

    result = build_eod_candidate_output(candidates, decisions)

    assert result.symbols == ("THYAO.IS",)


def test_v7_empty_input():
    result = build_eod_candidate_output(
        (),
        {},
    )

    assert result.symbols == ()
    assert result.count == 0
